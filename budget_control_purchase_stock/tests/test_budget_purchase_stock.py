# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from freezegun import freeze_time

from odoo import Command
from odoo.tests import Form, tagged

from odoo.addons.budget_control.tests.common import get_budget_common_class


@tagged("post_install", "-at_install")
class TestBudgetControlPurchaseStock(get_budget_common_class()):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        lines = [
            Command.create(
                {"analytic_account_id": cls.costcenter1.id, "amount": 2400.0}
            )
        ]
        cls.budget_plan = cls.create_budget_plan(
            cls,
            name=f"Test - Plan {cls.budget_period.name}",
            budget_period=cls.budget_period,
            lines=lines,
        )
        cls.budget_plan.action_confirm()
        cls.budget_plan.action_create_update_budget_control()
        cls.budget_plan.action_done()
        cls.budget_plan.invalidate_recordset()

        cls.budget_control = cls.budget_plan.budget_control_ids
        cls.budget_control.template_line_ids = [
            cls.template_line1.id,
            cls.template_line2.id,
            cls.template_line3.id,
        ]
        cls.budget_control.prepare_budget_control_matrix()
        assert len(cls.budget_control.line_ids) == 12
        # KPI1 = 100x4=400, KPI2=800, KPI3=1,200
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi1).write(
            {"amount": 100}
        )
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi2).write(
            {"amount": 200}
        )
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi3).write(
            {"amount": 300}
        )

        cls.valuation_account = cls.env["account.account"].create(
            {
                "name": "Test stock valuation",
                "code": "tv",
                "account_type": "liability_current",
                "reconcile": True,
                "company_ids": [Command.link(cls.env.ref("base.main_company").id)],
            }
        )
        cls.stock_input_account = cls.env["account.account"].create(
            {
                "name": "Test stock input",
                "code": "tsti",
                "account_type": "expense",
                "reconcile": True,
                "company_ids": [Command.link(cls.env.ref("base.main_company").id)],
            }
        )
        cls.stock_output_account = cls.env["account.account"].create(
            {
                "name": "Test stock output",
                "code": "tout",
                "account_type": "income",
                "reconcile": True,
                "company_ids": [Command.link(cls.env.ref("base.main_company").id)],
            }
        )
        cls.stock_journal = cls.env["account.journal"].create(
            {"name": "Stock Journal", "code": "STJTEST", "type": "general"}
        )

        # Add stock_output_account to KPI1 template line so outgoing DO JEs
        # (DR: stock_output, CR: stock_valuation) commit actual via budget system.
        cls.template_line1.write(
            {
                "account_ids": [
                    Command.link(cls.stock_output_account.id),
                    Command.link(cls.stock_input_account.id),
                    Command.link(cls.valuation_account.id),
                ]
            }
        )

        # Storable lot-tracked product mapped to KPI1.
        # is_storable=True + lot_valuated=True: creates SVL + valuation JE on
        # DO validate, enabling _recommit_via_valuation_lines to uncommit ST.
        cls.product_categ = cls.env.ref("product.product_category_5")
        cls.product_categ.update(
            {
                "property_valuation": "real_time",
                "property_stock_valuation_account_id": cls.valuation_account.id,
                "property_stock_account_input_categ_id": cls.stock_input_account.id,
                "property_stock_account_output_categ_id": cls.stock_output_account.id,
                "property_stock_journal": cls.stock_journal.id,
            }
        )

        cls.product_lot = cls.Product.create(
            {
                "name": "Product Lot",
                "type": "consu",
                "is_storable": True,
                "tracking": "lot",
                "lot_valuated": True,
                "standard_price": 50.0,
                "property_account_expense_id": cls.account_kpi1.id,
                "categ_id": cls.product_categ.id,
            }
        )
        cls.product_lot.product_tmpl_id.purchase_method = "purchase"

        # Outgoing picking type with budget commit enabled
        cls.warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.picking_type_out = cls.warehouse.out_type_id
        cls.picking_type_out.budget_commit = True
        # Pin the price source so tests don't depend on ambient DB config.
        # These tests assert stock commit from move price_unit (50), not lots.
        cls.picking_type_out.budget_price_source = "standard_price"
        cls.location_src = cls.picking_type_out.default_location_src_id
        cls.location_dest = cls.env.ref("stock.stock_location_customers")

        # 4 lots used across tests, standard_price matches product for SVL valuation
        Lot = cls.env["stock.lot"]
        cls.lot1 = Lot.create(
            {
                "name": "LOT-001",
                "product_id": cls.product_lot.id,
                "standard_price": 50.0,
            }
        )
        cls.lot2 = Lot.create(
            {
                "name": "LOT-002",
                "product_id": cls.product_lot.id,
                "standard_price": 50.0,
            }
        )
        cls.lot3 = Lot.create(
            {
                "name": "LOT-003",
                "product_id": cls.product_lot.id,
                "standard_price": 50.0,
            }
        )
        cls.lot4 = Lot.create(
            {
                "name": "LOT-004",
                "product_id": cls.product_lot.id,
                "standard_price": 50.0,
            }
        )

    @freeze_time("2001-02-01")
    def _create_purchase(self, po_lines):
        Purchase = self.env["purchase.order"]
        view_id = "purchase.purchase_order_form"
        with Form(Purchase, view=view_id) as po:
            po.partner_id = self.vendor
            po.date_order = datetime.today()
            for po_line in po_lines:
                with po.order_line.new() as line:
                    line.product_id = po_line["product_id"]
                    line.product_qty = po_line["product_qty"]
                    line.price_unit = po_line["price_unit"]
                    line.analytic_distribution = po_line["analytic_distribution"]
        return po.save()

    def _validate_receipt_with_lots(self, purchase, lots):
        """Validate incoming receipt from PO with 1 unit per lot."""
        receipt = purchase.picking_ids.filtered(
            lambda p: p.picking_type_code == "incoming"
        )
        receipt_move = receipt.move_ids[0]
        product = receipt_move.product_id
        # Remove any auto-created move_line_ids without lot assignment
        receipt_move.move_line_ids.unlink()
        for lot in lots:
            self.env["stock.move.line"].create(
                {
                    "move_id": receipt_move.id,
                    "picking_id": receipt.id,
                    "product_id": product.id,
                    "product_uom_id": product.uom_id.id,
                    "lot_id": lot.id,
                    "quantity": 1.0,
                    "location_id": receipt.location_id.id,
                    "location_dest_id": receipt.location_dest_id.id,
                }
            )
        receipt.with_context(skip_backorder=True).button_validate()

    def _create_delivery(self, move_lines):
        return self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_out.id,
                "location_id": self.location_src.id,
                "location_dest_id": self.location_dest.id,
                "move_ids_without_package": [
                    Command.create(
                        {
                            "name": line["product_id"].name,
                            "product_id": line["product_id"].id,
                            "product_uom_qty": line["product_qty"],
                            "product_uom": line["product_id"].uom_id.id,
                            "price_unit": line["price_unit"],
                            "analytic_distribution": line["analytic_distribution"],
                            "location_id": self.location_src.id,
                            "location_dest_id": self.location_dest.id,
                        }
                    )
                    for line in move_lines
                ],
            }
        )

    def _assign_lots_to_delivery(self, do, lots):
        """Manually assign each lot (1 unit) to the first move of a delivery."""
        move = do.move_ids[0]
        product = move.product_id
        # Drop the auto-reserved non-lot move line so quantity reflects only
        # the assigned lots (otherwise the move over-reserves).
        move.move_line_ids.unlink()
        for lot in lots:
            self.env["stock.move.line"].create(
                {
                    "move_id": move.id,
                    "picking_id": do.id,
                    "product_id": product.id,
                    "product_uom_id": product.uom_id.id,
                    "lot_id": lot.id,
                    "quantity": 1.0,
                    "location_id": do.location_id.id,
                    "location_dest_id": do.location_dest_id.id,
                }
            )

    @freeze_time("2001-02-01")
    def test_01_control_stock_from_po(self):
        """
        Lot-traced PO uncommit triggered by delivery lot assignment.
        (1) Confirm PO (qty=4, price=50) -> amount_purchase=200
        (2) Validate receipt with LOT-001..LOT-004
        (3) Confirm DO (qty=2, price=50) -> amount_stock=100, PO uncommit=100
        (4) Validate DO
        """
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"

        analytic_distribution = {str(self.costcenter1.id): 100}

        # (1) Confirm PO: qty=4, price=50 -> commit=200
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product_lot,
                    "product_qty": 4,
                    "price_unit": 50,
                    "analytic_distribution": analytic_distribution,
                }
            ]
        )
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_purchase, 200.0)
        self.assertAlmostEqual(self.budget_control.amount_stock, 0.0)

        # (2) Validate receipt with 4 lots (1 unit each)
        self._validate_receipt_with_lots(
            purchase, [self.lot1, self.lot2, self.lot3, self.lot4]
        )

        # (3) Confirm DO (qty=2, price=50)
        # - lots will auto assigned -> ST commit deferred, no PO uncommit
        do = self._create_delivery(
            [
                {
                    "product_id": self.product_lot,
                    "product_qty": 2,
                    "price_unit": 50,
                    "analytic_distribution": analytic_distribution,
                }
            ]
        )
        do.action_confirm()
        self.assertEqual(len(do.budget_move_ids), 1)
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_purchase, 100.0)
        self.assertAlmostEqual(self.budget_control.amount_stock, 100.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)

        # (4) Validate DO
        do.with_context(skip_backorder=True).button_validate()
        # Create 2 JE (from 2 lots)
        criteria1 = [["ref", "=", f"{do.name} - {do.product_id.name}"]]
        acc_moves = self.env["account.move"].search(criteria1)
        self.assertEqual(list(set(acc_moves.mapped("state"))), ["posted"])
        self.assertTrue(acc_moves.budget_move_ids)
        self.assertEqual(len(do.budget_move_ids), 3)
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_purchase, 100.0)
        self.assertAlmostEqual(self.budget_control.amount_stock, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 100.0)

        # (5) Cancel 1 JE
        acc_moves[0].button_draft()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_purchase, 100.0)
        self.assertAlmostEqual(self.budget_control.amount_stock, 50.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 50.0)

    @freeze_time("2001-02-01")
    def test_02_do_cancel_restores_po_commit(self):
        """
        Cancel DO removes lot-traced PBM entries and restores PO commitment.
        (1) Active DO with lots -> amount_purchase=100, amount_stock=100
        (2) Cancel DO -> lot-traced entries removed ->
            amount_purchase=200, amount_stock=0
        """
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"

        analytic_distribution = {str(self.costcenter1.id): 100}

        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product_lot,
                    "product_qty": 4,
                    "price_unit": 50,
                    "analytic_distribution": analytic_distribution,
                }
            ]
        )
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()
        self._validate_receipt_with_lots(
            purchase, [self.lot1, self.lot2, self.lot3, self.lot4]
        )

        do = self._create_delivery(
            [
                {
                    "product_id": self.product_lot,
                    "product_qty": 2,
                    "price_unit": 50,
                    "analytic_distribution": analytic_distribution,
                }
            ]
        )
        do.action_confirm()
        self._assign_lots_to_delivery(do, [self.lot1, self.lot2])
        do.recompute_budget_move()
        self.budget_control.invalidate_recordset()

        # (1) Lot-traced uncommit active
        self.assertAlmostEqual(self.budget_control.amount_purchase, 100.0)
        self.assertAlmostEqual(self.budget_control.amount_stock, 100.0)

        # (2) Cancel DO: _sync_lot_traced_po_uncommit removes entries and
        # triggers PO recompute - amount_purchase restored to full commit
        do.action_cancel()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_purchase, 200.0)
        self.assertAlmostEqual(self.budget_control.amount_stock, 0.0)

        PBM = self.env["purchase.budget.move"]
        stale = PBM.search([("stock_picking_id", "=", do.id)])
        self.assertFalse(stale)

    @freeze_time("2001-02-01")
    def test_03_no_analytic_do_skips_po_uncommit(self):
        """
        DO without analytic does not trigger lot-traced PO uncommit.
        Returning that DO and re-delivering with analytic uncommits correctly.
        (1) PO qty=4, price=50 -> amount_purchase=200
        (2) Validate receipt with LOT-001..LOT-004
        (3) DO1 (Lot1-4, no analytic) validate -> PO uncommit skipped -> 200
        (4) Return DO1 -> PO still 200, no stale PBM entries
        (5) DO2 (Lot1,2, analytic) confirm -> amount_purchase=100, amount_stock=100
        """
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"

        analytic_distribution = {str(self.costcenter1.id): 100}

        # (1) Confirm PO: qty=4, price=50 -> commit=200
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product_lot,
                    "product_qty": 4,
                    "price_unit": 50,
                    "analytic_distribution": analytic_distribution,
                }
            ]
        )
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()

        # (2) Validate receipt with 4 lots
        self._validate_receipt_with_lots(
            purchase, [self.lot1, self.lot2, self.lot3, self.lot4]
        )
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_purchase, 200.0)

        # (3) DO1: no analytic -> no ST commit -> no PO uncommit
        do1 = self._create_delivery(
            [
                {
                    "product_id": self.product_lot,
                    "product_qty": 4,
                    "price_unit": 50,
                    "analytic_distribution": {},
                }
            ]
        )
        do1.action_confirm()
        self._assign_lots_to_delivery(do1, [self.lot1, self.lot2, self.lot3, self.lot4])
        do1.recompute_budget_move()
        do1.with_context(skip_backorder=True).button_validate()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_purchase, 200.0)
        PBM = self.env["purchase.budget.move"]
        self.assertFalse(PBM.search([("stock_picking_id", "=", do1.id)]))

        # (4) Return DO1 -> lots back in stock, PO stays at 200
        return_wiz = (
            self.env["stock.return.picking"]
            .with_context(active_id=do1.id, active_model="stock.picking")
            .create({"picking_id": do1.id})
        )
        for return_line in return_wiz.product_return_moves:
            return_line.quantity = return_line.move_id.product_uom_qty
        action = return_wiz.action_create_returns()
        return_picking = self.env["stock.picking"].browse(action["res_id"])
        return_picking.with_context(skip_backorder=True).button_validate()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_purchase, 200.0)

        # (5) DO2: Lot1,2 with analytic -> uncommit Lot1,2 only = 100
        do2 = self._create_delivery(
            [
                {
                    "product_id": self.product_lot,
                    "product_qty": 2,
                    "price_unit": 50,
                    "analytic_distribution": analytic_distribution,
                }
            ]
        )
        do2.action_confirm()
        self._assign_lots_to_delivery(do2, [self.lot1, self.lot2])
        do2.recompute_budget_move()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_purchase, 100.0)
        self.assertAlmostEqual(self.budget_control.amount_stock, 100.0)

    @freeze_time("2001-02-01")
    def test_04_skip_vendor_bill_actual_when_stock_done(self):
        """
        PO + IN Picking (done) + OUT Picking (done with budget_commit=True)
        with analytic configured as stock_done -> vendor bill is marked
        not_affect_budget (header + line) and skips actual commitment.

        (1) Configure analytic plan to use stock_done as default actual source
        (2) PO + IN (done with lots) + OUT (done with lots, budget_commit=True)
            -> Stock actual recorded at DO JE
        (3) Create vendor bill from PO -> auto-flagged not_affect_budget
            (line-level via _compute_not_affect_budget_from_po, header via
            _check_not_affect_budget_cascade)
        (4) Post bill -> can_commit=False, no actual commit
        """
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"

        # Set preference to stock_done at plan level; analytic account inherits it.
        self.costcenter1.plan_id.budget_actual_source_default = "stock_done"
        self.costcenter1.budget_actual_source = False

        analytic_distribution = {str(self.costcenter1.id): 100}

        Lot = self.env["stock.lot"]
        l1 = Lot.create(
            {"name": "L-001", "product_id": self.product_lot.id, "standard_price": 50.0}
        )
        l2 = Lot.create(
            {"name": "L-002", "product_id": self.product_lot.id, "standard_price": 50.0}
        )
        l3 = Lot.create(
            {"name": "L-003", "product_id": self.product_lot.id, "standard_price": 50.0}
        )
        l4 = Lot.create(
            {"name": "L-004", "product_id": self.product_lot.id, "standard_price": 50.0}
        )

        # PO + IN (done) + OUT (done with budget_commit=True)
        purchase1 = self._create_purchase(
            [
                {
                    "product_id": self.product_lot,
                    "product_qty": 4,
                    "price_unit": 50,
                    "analytic_distribution": analytic_distribution,
                }
            ]
        )
        purchase1 = purchase1.with_context(force_date_commit=purchase1.date_order)
        purchase1.button_confirm()

        # Validate receipt (incoming picking)
        self._validate_receipt_with_lots(purchase1, [l1, l2, l3, l4])
        in_move1 = purchase1.picking_ids.filtered(
            lambda p: p.picking_type_code == "incoming"
        ).move_ids[0]

        # Create delivery picking (outgoing picking) with budget_commit=True
        self.picking_type_out.budget_commit = True
        do1 = self._create_delivery(
            [
                {
                    "product_id": self.product_lot,
                    "product_qty": 4,
                    "price_unit": 50,
                    "analytic_distribution": analytic_distribution,
                }
            ]
        )
        do1.action_confirm()
        out_move1 = do1.move_ids[0]

        # Link incoming to outgoing to simulate PO -> SO valuation flow
        in_move1.write({"move_dest_ids": [Command.link(out_move1.id)]})

        # Validate delivery picking
        self._assign_lots_to_delivery(do1, [l1, l2, l3, l4])
        do1.with_context(skip_backorder=True).button_validate()

        # Create Vendor Bill from PO -> not_affect_budget auto-flagged on
        # bill line from PO line analytic config; cascades to header.
        purchase1.action_create_invoice()
        bill1 = purchase1.invoice_ids[0]
        self.assertTrue(bill1.not_affect_budget)
        self.assertTrue(bill1.invoice_line_ids[0].not_affect_budget)
        # can_commit=False because not_affect_budget is set
        self.assertFalse(bill1.invoice_line_ids[0].can_commit)
        bill1.invoice_date = bill1.date
        bill1.action_post()

        # Bill does NOT commit actual (budget_move_ids is empty)
        # because actual already lives at stock done.
        self.assertTrue(bill1.not_affect_budget)
        self.assertFalse(bill1.invoice_line_ids.budget_move_ids)

    @freeze_time("2001-02-01")
    def test_05_non_lot_product_po_uncommit_flow(self):
        """
        Non-lot-tracked product (tracking='none') exercises the body of
        _apply_non_lot_po_uncommit_for_line.

        For lot-tracked products the function early-returns at
        ``if purchase_line.product_id.tracking != "none"`` so the body
        is never reached. Using a non-lot product we drive the full
        flow: PO commit -> receipt -> DO confirm (creates ST commit +
        PO uncommit via _uncommit_source_po_non_lot) -> PO recompute
        (re-applies the uncommit via _apply_non_lot_po_uncommit_for_line).

        (1) PO qty=4, price=50 -> amount_purchase=200
        (2) Validate receipt (no lots) -> 4 units in stock
        (3) DO confirmed with analytic ->
            - ST commit (qty=2, price=50) -> amount_stock=100
            - PO uncommit via _uncommit_source_po_non_lot -> amount_purchase=100
        (4) PO recompute (via order_line.recompute_budget_move) ->
            _apply_non_lot_po_uncommit_for_line re-applies the uncommit
        (5) budget state remains consistent (amount_purchase=100, not 200)
        """
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"

        # Non-lot product (tracking='none') so the early return in
        # _apply_non_lot_po_uncommit_for_line is bypassed.
        product_non_lot = self.Product.create(
            {
                "name": "Product Non-Lot",
                "type": "consu",
                "is_storable": True,
                "tracking": "none",
                "lot_valuated": False,
                "standard_price": 50.0,
                "property_account_expense_id": self.account_kpi1.id,
                "categ_id": self.product_categ.id,
            }
        )
        product_non_lot.product_tmpl_id.purchase_method = "purchase"

        analytic_distribution = {str(self.costcenter1.id): 100}

        # (1) Confirm PO: qty=4, price=50 -> commit=200
        purchase = self._create_purchase(
            [
                {
                    "product_id": product_non_lot,
                    "product_qty": 4,
                    "price_unit": 50,
                    "analytic_distribution": analytic_distribution,
                }
            ]
        )
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_purchase, 200.0)
        self.assertAlmostEqual(self.budget_control.amount_stock, 0.0)

        # (2) Validate receipt with no lots (qty=4 in a single move line).
        receipt = purchase.picking_ids.filtered(
            lambda p: p.picking_type_code == "incoming"
        )
        receipt_move = receipt.move_ids[0]
        receipt_move.move_line_ids.unlink()
        self.env["stock.move.line"].create(
            {
                "move_id": receipt_move.id,
                "picking_id": receipt.id,
                "product_id": product_non_lot.id,
                "product_uom_id": product_non_lot.uom_id.id,
                "quantity": 4.0,
                "location_id": receipt.location_id.id,
                "location_dest_id": receipt.location_dest_id.id,
            }
        )
        receipt.with_context(skip_backorder=True).button_validate()

        # (3) Confirm DO with analytic -> ST commit + PO uncommit (non-lot).
        self.picking_type_out.budget_commit = True
        do = self._create_delivery(
            [
                {
                    "product_id": product_non_lot,
                    "product_qty": 2,
                    "price_unit": 50,
                    "analytic_distribution": analytic_distribution,
                }
            ]
        )
        do.action_confirm()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 100.0)
        # PO uncommit (via _uncommit_source_po_non_lot) -> 200 - 100 = 100
        self.assertAlmostEqual(self.budget_control.amount_purchase, 100.0)

        # PBM entry created by _uncommit_source_po_non_lot for this DO
        PBM = self.env["purchase.budget.move"]
        initial_pbm_entries = PBM.search(
            [
                ("stock_picking_id", "=", do.id),
                ("purchase_line_id", "=", purchase.order_line.id),
            ]
        )
        self.assertEqual(len(initial_pbm_entries), 1)
        self.assertAlmostEqual(
            sum(initial_pbm_entries.mapped("amount_currency")), 100.0
        )

        # (4) Trigger PO recompute -> PurchaseOrderLine.recompute_budget_move
        # override collects done_pickings (the DO) and calls
        # _apply_po_uncommit_for_line -> _apply_non_lot_po_uncommit_for_line
        # (body runs because product is tracking='none').
        purchase.order_line.recompute_budget_move()
        self.budget_control.invalidate_recordset()

        # (5) Budget state remains consistent.
        # If _apply_non_lot_po_uncommit_for_line body did not run,
        # the uncommit would not be re-applied and amount_purchase
        # would be 200 (commit only).
        self.assertAlmostEqual(self.budget_control.amount_stock, 100.0)
        self.assertAlmostEqual(self.budget_control.amount_purchase, 100.0)

        # PBM entry is recreated with the same amount (proves body ran).
        final_pbm_entries = PBM.search(
            [
                ("stock_picking_id", "=", do.id),
                ("purchase_line_id", "=", purchase.order_line.id),
            ]
        )
        self.assertEqual(len(final_pbm_entries), 1)
        self.assertAlmostEqual(sum(final_pbm_entries.mapped("amount_currency")), 100.0)

    @freeze_time("2001-02-01")
    def test_06_account_move_not_affect_budget_with_stock_done(self):
        """
        Test: when an analytic is set to stock_done, the bill should be
        auto-marked as not_affect_budget.

        Flow:
        1. The system must expose "stock_done" as a valid option
           (via _selection_budget_actual_source).
        2. Configure costcenter1 to use stock_done -> the resolver should
           return "stock_done".
        3. Run the full flow: PO -> receive goods -> deliver (DO) -> create bill.
        4. The bill from the PO should be auto-marked not_affect_budget on
           both line and header, because the PO line's analytic is stock_done
           (the bill doesn't need to record budget, since it was already
           recorded at the DO).
        5. After posting the bill, no budget move should be created
           (commit_budget is a no-op).
        """
        # (1) The selection method on account.analytic.plan exposes stock_done.
        selection_keys = [
            key
            for key, _ in self.env[
                "account.analytic.plan"
            ]._selection_budget_actual_source()
        ]
        self.assertIn("stock_done", selection_keys)

        # (2) Configure the analytic to use stock_done and verify resolver.
        # Reset plan default so the analytic-level value is what decides.
        self.costcenter1.plan_id.budget_actual_source_default = False
        self.costcenter1.budget_actual_source = "stock_done"
        self.costcenter1.invalidate_recordset()
        self.assertEqual(
            self.costcenter1._get_effective_budget_actual_source(),
            "stock_done",
        )

        # (3-6) Drive a full PO -> DO (done) -> vendor bill flow.
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"

        analytic_distribution = {str(self.costcenter1.id): 100}

        Lot = self.env["stock.lot"]
        l1 = Lot.create(
            {
                "name": "NS-001",
                "product_id": self.product_lot.id,
                "standard_price": 50.0,
            }
        )
        l2 = Lot.create(
            {
                "name": "NS-002",
                "product_id": self.product_lot.id,
                "standard_price": 50.0,
            }
        )

        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product_lot,
                    "product_qty": 2,
                    "price_unit": 50,
                    "analytic_distribution": analytic_distribution,
                }
            ]
        )
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()
        self._validate_receipt_with_lots(purchase, [l1, l2])

        self.picking_type_out.budget_commit = True
        do = self._create_delivery(
            [
                {
                    "product_id": self.product_lot,
                    "product_qty": 2,
                    "price_unit": 50,
                    "analytic_distribution": analytic_distribution,
                }
            ]
        )
        do.action_confirm()
        self._assign_lots_to_delivery(do, [l1, l2])
        do.with_context(skip_backorder=True).button_validate()

        # (3) Vendor bill from PO is auto-flagged not_affect_budget at line
        # level from PO line analytic config (per
        # AccountMove._compute_not_affect_budget_from_po).
        purchase.action_create_invoice()
        bill = purchase.invoice_ids[0]
        self.assertTrue(bill.invoice_line_ids[0].not_affect_budget)

        # (4) Header cascades via _check_not_affect_budget_cascade.
        self.assertTrue(bill.not_affect_budget)

        # (5) can_commit is False, so commit_budget is a no-op on post.
        self.assertFalse(bill.invoice_line_ids[0].can_commit)

        # (6) Post bill -> no actual commit (budget_move_ids empty).
        bill.invoice_date = bill.date
        bill.action_post()
        self.assertFalse(bill.invoice_line_ids.budget_move_ids)
