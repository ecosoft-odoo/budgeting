# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.budget_control.tests.common import get_budget_common_class


@tagged("post_install", "-at_install")
class TestBudgetControlStock(get_budget_common_class()):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        # Create budget plan with 1 analytic
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

        # Refresh data
        cls.budget_plan.invalidate_recordset()

        cls.budget_control = cls.budget_plan.budget_control_ids
        cls.budget_control.template_line_ids = [
            cls.template_line1.id,
            cls.template_line2.id,
            cls.template_line3.id,
        ]

        # Test item created for 3 kpi x 4 quarters = 12 budget items
        cls.budget_control.prepare_budget_control_matrix()
        assert len(cls.budget_control.line_ids) == 12
        # Assign budget.control amount: KPI1 = 100x4=400, KPI2=800, KPI3=1,200
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi1).write(
            {"amount": 100}
        )
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi2).write(
            {"amount": 200}
        )
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi3).write(
            {"amount": 300}
        )

        # Stock valuation accounts (needed for validate->JE flow tests)
        cls.valuation_account = cls.env["account.account"].create(
            {
                "name": "Test stock valuation",
                "code": "tv",
                "account_type": "liability_current",
                "reconcile": True,
            }
        )
        cls.stock_output_account = cls.env["account.account"].create(
            {
                "name": "Test stock output",
                "code": "tout",
                "account_type": "income",
                "reconcile": True,
            }
        )
        cls.stock_journal = cls.env["account.journal"].create(
            {"name": "Stock Journal", "code": "STJTEST", "type": "general"}
        )

        # Product category with real-time valuation
        cls.product_categ = cls.env.ref("product.product_category_5")
        cls.product_categ.update(
            {
                "property_valuation": "real_time",
                "property_stock_valuation_account_id": cls.valuation_account.id,
                "property_stock_account_output_categ_id": cls.stock_output_account.id,
                "property_stock_journal": cls.stock_journal.id,
            }
        )
        # Keep stock fixtures explicit when the optional purchase bridge is loaded.
        (cls.product1 | cls.product2).write(
            {"is_storable": True, "categ_id": cls.product_categ.id}
        )
        if "budget_inventory_actual_source" in cls.product_categ._fields:
            cls.env.company.budget_inventory_actual_source = "stock_issue"
            cls.product_categ.budget_inventory_actual_source = "stock_issue"

        # Additional products for flow tests
        cls.product_std = cls.Product.create(
            {
                "name": "Product Standard",
                "type": "consu",
                "is_storable": True,
                "standard_price": 100.0,
                "property_account_expense_id": cls.account_kpi1.id,
                "categ_id": cls.product_categ.id,
            }
        )
        cls.product_lot = cls.Product.create(
            {
                "name": "Product Lot",
                "type": "consu",
                "is_storable": True,
                "tracking": "lot",
                "standard_price": 50.0,
                "property_account_expense_id": cls.account_kpi1.id,
                "categ_id": cls.product_categ.id,
            }
        )
        Lot = cls.env["stock.lot"]
        cls.lot1 = Lot.create(
            {
                "name": "LOT-001",
                "product_id": cls.product_lot.id,
                "standard_price": 40.0,
            }
        )
        cls.lot2 = Lot.create(
            {
                "name": "LOT-002",
                "product_id": cls.product_lot.id,
                "standard_price": 60.0,
            }
        )

        # Link stock_output_account to KPI1 template so JE lines commit actual
        cls.template_line1.write(
            {"account_ids": [Command.link(cls.stock_output_account.id)]}
        )

        # Warehouse and picking type
        cls.warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.picking_type = cls.warehouse.out_type_id
        cls.picking_type.budget_commit = True
        cls.picking_type.budget_price_source = "standard_price"
        cls.location_src = cls.picking_type.default_location_src_id
        cls.location_dest = cls.env.ref("stock.stock_location_customers")

    def _set_qty_on_hand(self, product, qty, lot=None):
        self.env["stock.quant"]._update_available_quantity(
            product, self.location_src, qty, lot_id=lot
        )

    def _assign_lots_to_move(self, move, lot_qty_pairs):
        move.move_line_ids.unlink()
        for lot, qty in lot_qty_pairs:
            self.env["stock.move.line"].create(
                {
                    "move_id": move.id,
                    "picking_id": move.picking_id.id,
                    "product_id": move.product_id.id,
                    "product_uom_id": move.product_uom.id,
                    "lot_id": lot.id,
                    "quantity": qty,
                    "location_id": move.location_id.id,
                    "location_dest_id": move.location_dest_id.id,
                }
            )

    def _create_picking(self, picking_lines):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type.id,
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
                    for line in picking_lines
                ],
            }
        )
        return picking

    @freeze_time("2001-02-01")
    def test_01_budget_stock(self):
        """
        On Stock Picking
        (1) Confirm picking with amount exceeding budget -> raises UserError
        (2) Confirm picking within budget -> succeeds and automatically commits budget.
        (3) Modify picking lines to exceed budget -> raises UserError
        (4) Modify picking lines within budget ->
            automatically recomputes and adjusts commitment.
        (5) Cancel picking -> budget commitment is deleted.
        """
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)

        # Prepare Stock Picking (exceeds budget)
        analytic_distribution = {str(self.costcenter1.id): 100}
        picking = self._create_picking(
            [
                {
                    "product_id": self.product1,  # KPI1
                    "product_qty": 1,
                    "price_unit": 401,  # Exceeds budget of KPI1 (400)
                    "analytic_distribution": analytic_distribution,
                }
            ]
        )

        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic_kpi"

        # (1) Confirm picking with amount exceeding budget -> should fail
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            picking.action_confirm()

        # Adjust price to be within budget
        picking.move_ids_without_package[0].write({"price_unit": 300})
        # (2) Confirm picking within budget -> should succeed and auto commit
        picking.action_confirm()
        self.assertIn(picking.state, ["confirmed", "assigned", "waiting"])
        self.assertAlmostEqual(self.budget_control.amount_stock, 300.0)

        # (3) Modify picking lines to exceed budget -> should fail
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            picking.write(
                {
                    "move_ids_without_package": [
                        Command.update(
                            picking.move_ids_without_package[0].id, {"price_unit": 500}
                        )
                    ]
                }
            )

        # (4) Modify picking lines within budget -> automatically recomputes
        picking.write(
            {
                "move_ids_without_package": [
                    Command.update(
                        picking.move_ids_without_package[0].id, {"price_unit": 350}
                    )
                ]
            }
        )
        self.assertAlmostEqual(self.budget_control.amount_stock, 350.0)

        # (5) Cancel picking -> budget commitment is deleted
        picking.action_cancel()
        self.assertAlmostEqual(self.budget_control.amount_stock, 0.0)

    @freeze_time("2001-02-01")
    def test_02_budget_stock_no_control(self):
        """
        (1) stock control enabled -> amount exceeds budget -> UserError
        (2) budget_period.stock=False -> stock control disabled -> no error
        """
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)

        self.budget_period.control_budget = True
        self.assertTrue(self.budget_period.stock)
        self.budget_period.control_level = "analytic_kpi"
        analytic_distribution = {str(self.costcenter1.id): 100}
        picking = self._create_picking(
            [
                {
                    "product_id": self.product1,  # KPI1 = 401 -> error
                    "product_qty": 1,
                    "price_unit": 401,
                    "analytic_distribution": analytic_distribution,
                }
            ]
        )

        # (1) stock control enabled -> budget check fails
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            picking.action_confirm()

        # (2) disable stock control specifically -> no error
        self.budget_period.stock = False
        picking.action_confirm()
        self.assertIn(picking.state, ["confirmed", "assigned", "waiting"])

    @freeze_time("2001-02-01")
    def test_03_budget_stock_recompute_close(self):
        """
        (1) Confirm two-line picking -> commits budget
        (2) Explicit recompute -> same amount
        (3) close_budget_move -> clears commitment
        """
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)

        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        analytic_distribution = {str(self.costcenter1.id): 100}
        picking = self._create_picking(
            [
                {
                    "product_id": self.product1,  # KPI1 = 2*150 = 300
                    "product_qty": 2,
                    "price_unit": 150,
                    "analytic_distribution": analytic_distribution,
                },
                {
                    "product_id": self.product2,  # KPI2 = 4*100 = 400
                    "product_qty": 4,
                    "price_unit": 100,
                    "analytic_distribution": analytic_distribution,
                },
            ]
        )
        picking.action_confirm()
        # Budget Created
        self.assertTrue(picking.budget_move_ids)
        self.budget_control.invalidate_recordset()
        # Stock commit = (2*150) + (4*100) = 700
        self.assertAlmostEqual(self.budget_control.amount_stock, 700.0)

        # Recompute -> same result
        picking.recompute_budget_move()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 700.0)

        # Close -> clears commitment
        picking.close_budget_move()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 0.0)

    @freeze_time("2001-02-01")
    def test_04_standard_price_full_flow(self):
        """Non-lot product: confirm -> commit -> validate -> actual on JE.

        Budget timeline:
        (1) Draft -> no budget movement
        (2) Confirm -> stock.budget.move created (commitment, uses price_unit)
        (3) Validate -> stock valuation JE posted ->
            - stock.budget.move uncommit (credit)
            - account.budget.move created (actual, uses standard_price)
        """
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        analytic_dist = {str(self.costcenter1.id): 100}
        self._set_qty_on_hand(self.product_std, 1)

        # (1) Draft — no budget
        do = self._create_picking(
            [
                {
                    "product_id": self.product_std,
                    "product_qty": 1,
                    "price_unit": 300,
                    "analytic_distribution": analytic_dist,
                }
            ]
        )
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)

        # (2) Confirm -> commit (uses price_unit=300)
        do.action_confirm()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 300.0)
        self.assertEqual(len(do.budget_move_ids), 1)
        self.assertEqual(do.budget_move_ids.move_id, do.move_ids)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)

        # (3) action_assign -> recompute (already assigned, same amount)
        do.action_assign()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 300.0)

        # (4) do_unreserve -> no move lines, budget stays committed (non-lot)
        do.do_unreserve()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 300.0)

        # Re-assign before validate
        do.action_assign()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 300.0)

        # (5) Validate -> valuation JE posted
        # JE uses SVL value = standard_price * qty = 100
        do.with_context(skip_backorder=True).button_validate()
        self.assertEqual(do.state, "done")

        # Stock commitment released (uncommit = credit)
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 0.0)
        # Actual from JE: stock_output line commits at SVL value (100)
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_actual, 100.0)

    @freeze_time("2001-02-01")
    def test_05_lot_product_standard_price_flow(self):
        """Lot product with standard_price source: 2 lots (unit=40,60).

        Budget timeline:
        (1) 2 lots -> commit uses price_unit (50), qty=2 -> 100
        (2) Validate -> 2 JEs (one per lot) -> uncommit per-lot + actual=100
        """
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        analytic_dist = {str(self.costcenter1.id): 100}
        self._set_qty_on_hand(self.product_lot, 1, self.lot1)
        self._set_qty_on_hand(self.product_lot, 1, self.lot2)

        do = self._create_picking(
            [
                {
                    "product_id": self.product_lot,
                    "product_qty": 2,
                    "price_unit": 50,
                    "analytic_distribution": analytic_dist,
                }
            ]
        )
        do.action_confirm()
        move = do.move_ids[0]
        self._assign_lots_to_move(move, [(self.lot1, 1.0), (self.lot2, 1.0)])
        # action_assign triggers recompute via override
        do.action_assign()

        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 100.0)
        self.assertEqual(len(do.budget_move_ids), 1)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)

        # do_unreserve -> lots removed, no lots to commit -> budget cleared
        do.do_unreserve()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 0.0)

        # Re-assign lots and recompute via action_assign -> budget restored
        self._assign_lots_to_move(move, [(self.lot1, 1.0), (self.lot2, 1.0)])
        do.action_assign()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 100.0)

        # Validate -> 2 JEs
        do.with_context(skip_backorder=True).button_validate()
        self.assertEqual(do.state, "done")

        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 0.0)
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_actual, 100.0)

    @freeze_time("2001-02-01")
    def test_06_lot_product_lot_price_flow(self):
        """Lot product with lot_price source: 2 lots (unit=40,60).

        Budget timeline:
        (1) 2 lots -> lot_price commit per-lot = lot1:40 + lot2:60 = 100
        (2) 2 stock.budget.move (one per lot, not weighted avg)
        (3) Validate -> 2 JEs -> uncommit per-lot exact match + actual=100
        """
        self.picking_type.budget_price_source = "lot_price"
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        analytic_dist = {str(self.costcenter1.id): 100}
        self._set_qty_on_hand(self.product_lot, 1, self.lot1)
        self._set_qty_on_hand(self.product_lot, 1, self.lot2)

        do = self._create_picking(
            [
                {
                    "product_id": self.product_lot,
                    "product_qty": 2,
                    "price_unit": 50,
                    "analytic_distribution": analytic_dist,
                }
            ]
        )
        do.action_confirm()
        move = do.move_ids[0]
        self._assign_lots_to_move(move, [(self.lot1, 1.0), (self.lot2, 1.0)])
        # action_assign triggers per-lot commit via override
        do.action_assign()

        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 100.0)
        self.assertEqual(len(do.budget_move_ids), 2)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)

        # do_unreserve -> lots removed, no lots to commit -> budget cleared
        do.do_unreserve()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 0.0)

        # Re-assign lots and recompute via action_assign -> per-lot commit restored
        self._assign_lots_to_move(move, [(self.lot1, 1.0), (self.lot2, 1.0)])
        do.action_assign()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 100.0)
        self.assertEqual(len(do.budget_move_ids), 2)

        do.with_context(skip_backorder=True).button_validate()
        self.assertEqual(do.state, "done")

        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 0.0)
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_actual, 100.0)

    @freeze_time("2001-02-01")
    def test_07_cancel_after_commit_clears_budget(self):
        """Confirm (commit) -> Cancel -> budget cleared, no actual."""
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        analytic_dist = {str(self.costcenter1.id): 100}
        self._set_qty_on_hand(self.product_std, 1)

        do = self._create_picking(
            [
                {
                    "product_id": self.product_std,
                    "product_qty": 1,
                    "price_unit": 300,
                    "analytic_distribution": analytic_dist,
                }
            ]
        )
        do.action_confirm()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 300.0)

        # action_assign -> no change
        do.action_assign()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 300.0)

        # do_unreserve -> no move lines, budget stays committed (non-lot)
        do.do_unreserve()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 300.0)

        # Re-assign before cancel
        do.action_assign()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 300.0)

        do.action_cancel()
        self.assertEqual(do.state, "cancel")
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)

    @freeze_time("2001-02-01")
    def test_08_reset_je_to_draft_restores_budget(self):
        """Validate -> JE posted -> reset JE to draft -> stock budget restored."""
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        analytic_dist = {str(self.costcenter1.id): 100}
        self._set_qty_on_hand(self.product_std, 1)

        do = self._create_picking(
            [
                {
                    "product_id": self.product_std,
                    "product_qty": 1,
                    "price_unit": 300,
                    "analytic_distribution": analytic_dist,
                }
            ]
        )
        do.action_confirm()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 300.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)

        do.action_assign()
        do.with_context(skip_backorder=True).button_validate()
        self.assertEqual(do.state, "done")

        # After validate: JE posted -> stock budget becomes actual
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 0.0)

        # Get valuation JE and reset to draft
        svl = do.move_ids.stock_valuation_layer_ids
        je = svl.account_move_id
        self.assertEqual(je.state, "posted")
        je.button_draft()
        self.assertEqual(je.state, "draft")

        # Budget should be restored after JE reset to draft
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 300.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)

    @freeze_time("2001-02-01")
    def test_09_unlink_confirmed_picking_clears_budget(self):
        """Confirm (commit) -> unlink picking -> budget cleared, no orphan moves."""
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        analytic_dist = {str(self.costcenter1.id): 100}
        self._set_qty_on_hand(self.product_std, 1)

        do = self._create_picking(
            [
                {
                    "product_id": self.product_std,
                    "product_qty": 1,
                    "price_unit": 300,
                    "analytic_distribution": analytic_dist,
                }
            ]
        )
        do.action_confirm()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 300.0)
        self.assertTrue(do.budget_move_ids)
        do.unlink()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)
        # Verify no orphan stock.budget.move left behind
        orphan = self.env["stock.budget.move"].search(
            [("move_id", "=", False), ("picking_id", "=", False)]
        )
        self.assertFalse(orphan)

    @freeze_time("2001-02-01")
    def test_10_svl_je_not_affect_budget_by_picking_type(self):
        """
        Without an upstream move, the SVL JE's not_affect_budget flag mirrors
        the valuation move's picking type budget_commit setting.

        (1) Picking type WITHOUT budget_commit: validating creates an SVL JE
            that is flagged not_affect_budget and records no actual.
        (2) Picking type WITH budget_commit: validating creates an SVL JE
            that is NOT flagged and records actual normally.
        """
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        analytic_dist = {str(self.costcenter1.id): 100}

        # --- (1) Picking type WITHOUT budget_commit -> not_affect_budget ---
        self.picking_type.budget_commit = False
        self._set_qty_on_hand(self.product_std, 1)
        do_no_commit = self._create_picking(
            [
                {
                    "product_id": self.product_std,
                    "product_qty": 1,
                    "price_unit": 100,
                    "analytic_distribution": analytic_dist,
                }
            ]
        )
        do_no_commit.action_confirm()
        do_no_commit.action_assign()
        do_no_commit.with_context(skip_backorder=True).button_validate()
        self.assertEqual(do_no_commit.state, "done")
        je_no_commit = do_no_commit.move_ids.stock_valuation_layer_ids.account_move_id
        self.assertTrue(je_no_commit)
        self.assertTrue(je_no_commit.not_affect_budget)
        # No stock commit (no budget_commit on the type) and no actual.
        self.assertFalse(do_no_commit.budget_move_ids)
        self.assertFalse(je_no_commit.line_ids.budget_move_ids)

        # --- (2) Picking type WITH budget_commit -> NOT not_affect_budget ---
        self.picking_type.budget_commit = True
        self._set_qty_on_hand(self.product_std, 1)
        do_commit = self._create_picking(
            [
                {
                    "product_id": self.product_std,
                    "product_qty": 1,
                    "price_unit": 100,
                    "analytic_distribution": analytic_dist,
                }
            ]
        )
        do_commit.action_confirm()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_stock, 100.0)
        do_commit.action_assign()
        do_commit.with_context(skip_backorder=True).button_validate()
        self.assertEqual(do_commit.state, "done")
        je_commit = do_commit.move_ids.stock_valuation_layer_ids.account_move_id
        self.assertTrue(je_commit)
        self.assertFalse(je_commit.not_affect_budget)
        # After validate: JE posted -> stock commit becomes actual.
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_actual, 100.0)

    def test_11_svl_je_uses_upstream_two_step_budget_source(self):
        """A DO valuation uses the budget commitment from its upstream PICK."""
        analytic_dist = {str(self.costcenter1.id): 100}
        output_location = self.warehouse.wh_output_stock_loc_id
        output_location.active = True
        pick_type = self.warehouse.pick_type_id
        pick_type.update(
            {
                "active": True,
                "budget_commit": True,
                "budget_price_source": "standard_price",
            }
        )
        self.picking_type.budget_commit = False

        delivery = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type.id,
                "location_id": output_location.id,
                "location_dest_id": self.location_dest.id,
                "move_ids_without_package": [
                    Command.create(
                        {
                            "name": self.product_std.name,
                            "product_id": self.product_std.id,
                            "product_uom_qty": 1,
                            "product_uom": self.product_std.uom_id.id,
                            "price_unit": 100,
                            "analytic_distribution": analytic_dist,
                            "location_id": output_location.id,
                            "location_dest_id": self.location_dest.id,
                        }
                    )
                ],
            }
        )
        pick = self.env["stock.picking"].create(
            {
                "picking_type_id": pick_type.id,
                "location_id": self.location_src.id,
                "location_dest_id": output_location.id,
                "move_ids_without_package": [
                    Command.create(
                        {
                            "name": self.product_std.name,
                            "product_id": self.product_std.id,
                            "product_uom_qty": 1,
                            "product_uom": self.product_std.uom_id.id,
                            "price_unit": 100,
                            "analytic_distribution": analytic_dist,
                            "location_id": self.location_src.id,
                            "location_dest_id": output_location.id,
                            "move_dest_ids": [Command.link(delivery.move_ids.id)],
                        }
                    )
                ],
            }
        )

        delivery_move = delivery.move_ids
        self.assertEqual(delivery_move._get_budget_commit_source_moves(), pick.move_ids)
        valuation_entry = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": self.stock_journal.id,
                "stock_move_id": delivery_move.id,
                "line_ids": [
                    Command.create(
                        {
                            "name": "Two-step valuation",
                            "account_id": self.stock_output_account.id,
                            "balance": 100,
                            "analytic_distribution": analytic_dist,
                        }
                    ),
                    Command.create(
                        {
                            "name": "Two-step valuation",
                            "account_id": self.valuation_account.id,
                            "balance": -100,
                        }
                    ),
                ],
            }
        )
        self.assertFalse(valuation_entry.not_affect_budget)
