# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, tagged

from odoo.addons.budget_control.models.analytic_plan import budget_row_key
from odoo.addons.budget_control.tests.common import get_budget_common_class


@tagged("post_install", "-at_install")
class TestBudgetControlPurchase(get_budget_common_class()):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        cls.budget_control = cls.create_budget_control(cls, cls.costcenter1, 2400.0)
        # Test item created for 3 kpi x 4 quarters = 12 budget items
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

        # Purchase method
        cls.product1.product_tmpl_id.purchase_method = "purchase"
        cls.product2.product_tmpl_id.purchase_method = "purchase"

    @freeze_time("2001-02-01")
    def _create_purchase(self, po_lines):
        Purchase = self.env["purchase.order"]
        view_id = "purchase.purchase_order_form"
        with Form(Purchase, view=view_id) as po:
            po.partner_id = self.vendor
            po.date_order = fields.Datetime.now()
            for po_line in po_lines:
                with po.order_line.new() as line:
                    line.product_id = po_line["product_id"]
                    line.product_qty = po_line["product_qty"]
                    line.price_unit = po_line["price_unit"]
                    line.analytic_distribution = po_line["analytic_distribution"]
        purchase = po.save()
        return purchase

    def _create_period(self, year):
        return self.env["budget.period"].create(
            {
                "name": f"Budget for FY{year}",
                "template_id": self.template.id,
                "bm_date_from": f"{year}-01-01",
                "bm_date_to": f"{year}-12-31",
                "plan_date_range_type_id": self.date_range_type.id,
            }
        )

    def _forward_commitments(self, period):
        forward = self.CommitForward.create(
            {"name": f"Forward to {period.name}", "to_budget_period_id": period.id}
        )
        forward.action_review_budget_commit()
        return forward

    def _get_consumptions(self, analytics):
        """``{(period, analytic, amount type): amount}`` of the commitments and
        actuals of ``analytics``, but zero ones."""
        self.env.flush_all()
        groups = (
            self.env["budget.monitor.report"]
            .sudo()
            ._read_group(
                [
                    ("analytic_account_id", "in", analytics.ids),
                    ("amount_type", "not in", ("10_budget", "12_forward_out")),
                ],
                ["budget_period_id", "analytic_account_id", "amount_type"],
                ["amount:sum"],
            )
        )
        return {
            (period, analytic, amount_type): amount
            for period, analytic, amount_type, amount in groups
            if amount
        }

    def _bill_purchase(self, purchase, date):
        with freeze_time(date):
            purchase = purchase.with_context(force_date_commit=False)
            purchase.action_create_invoice()
            bill = purchase.invoice_ids
            bill.invoice_date = bill.date
            bill.action_post()
        return bill

    @freeze_time("2001-02-01")
    def test_01_budget_purchase(self):
        """
        On Purchase Order
        (1) Test case, no budget check -> OK
        (2) Check Budget with analytic_kpi -> Error amount exceed on kpi1
        (3) Check Budget with analytic -> OK
        (2) Check Budget with analytic -> Error amount exceed
        """
        # Controlled budget
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)
        # Prepare PO
        analytic_distribution = {str(self.costcenter1.id): 100}
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product1,  # KPI1 = 401 -> error
                    "product_qty": 1,
                    "price_unit": 401,
                    "analytic_distribution": analytic_distribution,
                },
                {
                    "product_id": self.product2,  # KPI2 = 798
                    "product_qty": 2,
                    "price_unit": 399,
                    "analytic_distribution": analytic_distribution,
                },
            ]
        )

        # (1) No budget check first
        self.budget_period.control_budget = False
        self.budget_period.control_level = "analytic_kpi"
        # force date commit, as freeze_time not work for write_date
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()  # No budget check no error
        self.assertTrue(purchase.budget_move_ids)

        # (2) Check Budget with analytic_kpi -> Error
        purchase.button_cancel()
        purchase.button_draft()
        self.budget_period.control_budget = True  # Set to check budget
        self.assertTrue(self.budget_period.purchase)
        # kpi 1 (kpi1) & CostCenter1, will result in $ -1.00
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            purchase.button_confirm()
        # (3) Check Budget with analytic -> OK
        purchase.button_cancel()
        purchase.button_draft()
        self.budget_period.control_level = "analytic"
        purchase.button_confirm()

        self.assertAlmostEqual(
            self.budget_control.amount_balance, 1201.0
        )  # 2400 - (798 + 401)
        purchase.button_cancel()
        self.assertAlmostEqual(self.budget_control.amount_balance, 2400.0)
        # (4) Change amount from 2 * 399 to 2 * 1000
        purchase.order_line[1].price_unit = 1000
        purchase.button_draft()
        # CostCenter1, will result in $ -1.00
        with self.assertRaises(UserError):
            purchase.button_confirm()

    @freeze_time("2001-02-01")
    def test_02_budget_purchase_no_control(self):
        # Controlled budget
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)

        self.budget_period.control_budget = True
        self.assertTrue(self.budget_period.purchase)
        self.assertEqual(self.budget_period.control_level, "analytic_kpi")

        # Prepare PO
        analytic_distribution = {str(self.costcenter1.id): 100}
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product1,  # KPI1 = 401 -> error
                    "product_qty": 1,
                    "price_unit": 401,
                    "analytic_distribution": analytic_distribution,
                },
                {
                    "product_id": self.product2,  # KPI2 = 798
                    "product_qty": 2,
                    "price_unit": 399,
                    "analytic_distribution": analytic_distribution,
                },
            ]
        )
        purchase = purchase.with_context(force_date_commit=purchase.date_order)

        # kpi 1 (kpi1) & CostCenter1, will result in $ -1.00
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            purchase.button_confirm()

        # Not control purchase (specific)
        self.budget_period.purchase = False
        purchase.button_confirm()

    @freeze_time("2001-02-01")
    def test_03_budget_purchase_to_invoice(self):
        """Purchase to Invoice, commit and uncommit"""
        # Controlled budget
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)

        # Prepare PO on kpi1 with qty 4 and unit_price 600
        analytic_distribution = {str(self.costcenter1.id): 100}
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product1,  # KPI1 = 2400
                    "product_qty": 4,
                    "price_unit": 600,
                    "analytic_distribution": analytic_distribution,
                },
            ]
        )
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()
        original_purchase_move_ids = set(purchase.budget_move_ids.ids)
        # PO Commit = 2400, INV Actual = 0, Balance = 0
        self.assertAlmostEqual(self.budget_control.amount_commit, 2400.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 0.0)
        # Create and post invoice
        purchase.action_create_invoice()
        self.assertEqual(purchase.invoice_status, "invoiced")
        invoice = purchase.invoice_ids[:1]
        # Change qty to 1
        invoice.with_context(check_move_validity=False).invoice_line_ids[0].quantity = 1
        invoice.invoice_date = invoice.date
        invoice.action_post()
        # Posting a bill only adds its PO reversal; it must not rebuild the
        # original PO commitments (a costly O(lines) delete/create cycle).
        self.assertTrue(
            original_purchase_move_ids.issubset(purchase.budget_move_ids.ids)
        )
        # PO Commit = 1800, INV Actual = 600, Balance = 0
        self.assertAlmostEqual(self.budget_control.amount_commit, 1800.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 600.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 0.0)
        # Cancel invoice
        invoice.button_cancel()
        self.assertAlmostEqual(self.budget_control.amount_commit, 2400.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 0.0)

    @freeze_time("2001-02-01")
    def test_03_budget_recompute_and_close_budget_move(self):
        """Purchase to Invoice (partial)
        - Test recompute on both Purchase and Invoice
        - Test close on both Purchase and Invoice"""
        # Controlled budget
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)

        analytic_distribution = {str(self.costcenter1.id): 100}
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product1,  # KPI1 = 300
                    "product_qty": 2,
                    "price_unit": 150,
                    "analytic_distribution": analytic_distribution,
                },
                {
                    "product_id": self.product2,  # KPI2 = 400
                    "product_qty": 4,
                    "price_unit": 100,
                    "analytic_distribution": analytic_distribution,
                },
            ]
        )
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()
        # PO Commit = 700, INV Actual = 0
        self.assertAlmostEqual(self.budget_control.amount_purchase, 700.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)

        # Create and post invoice
        purchase.action_create_invoice()
        self.assertEqual(purchase.invoice_status, "invoiced")
        invoice = purchase.invoice_ids[:1]
        # Change qty to 1 and 3
        invoice = invoice.with_context(check_move_validity=False)
        invoice.invoice_line_ids[0].quantity = 1
        invoice.invoice_line_ids[1].quantity = 3
        invoice.invoice_date = invoice.date
        invoice.action_post()
        # PO Commit = 700-450 = 250.0 , INV Actual = (1*150) + (3*100) = 450.0
        self.assertAlmostEqual(self.budget_control.amount_purchase, 250.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 450.0)
        # Test recompute, must be same
        purchase.recompute_budget_move()
        self.assertAlmostEqual(self.budget_control.amount_purchase, 250.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 450.0)
        invoice.recompute_budget_move()
        self.assertAlmostEqual(self.budget_control.amount_purchase, 250.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 450.0)
        # Test close budget move
        purchase.close_budget_move()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_purchase, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 450.0)
        # Test close budget move
        invoice.close_budget_move()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_purchase, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)

    @freeze_time("2001-02-01")
    def test_04_confirmed_line_edit_and_manual_recompute(self):
        """State-write guard must not suppress later intentional recomputes."""
        self.budget_control.action_submit()
        self.budget_control.action_done()

        analytic_distribution = {str(self.costcenter1.id): 100}
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product1,
                    "product_qty": 2,
                    "price_unit": 100,
                    "analytic_distribution": analytic_distribution,
                }
            ]
        ).with_context(force_date_commit=fields.Datetime.now())
        purchase.button_confirm()
        self.assertAlmostEqual(self.budget_control.amount_purchase, 200.0)

        # Editing an approved PO through its order_line commands must trigger
        # the constraint normally; the skip flag is set only on state writes.
        purchase.write(
            {
                "order_line": [
                    Command.update(purchase.order_line.id, {"price_unit": 150})
                ]
            }
        )
        self.assertAlmostEqual(self.budget_control.amount_purchase, 300.0)

        # The object button invokes this method without the internal skip
        # context and must always rebuild the commitment from current values.
        purchase.order_line.write({"price_unit": 175})
        purchase.recompute_budget_move()
        self.assertAlmostEqual(self.budget_control.amount_purchase, 350.0)

    @freeze_time("2001-02-01")
    def test_05_purchase_analytic_rows(self):
        """A purchase line commits each row of its analytic distribution, e.g.
        CostCenter1 by Fund A 60% and Fund B 40%, and its bills return each
        row."""
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.budget_period.write({"control_budget": True, "control_level": "analytic"})
        fund_plan = self.AnalyticPlan.create({"name": "Fund", "control_budget": False})
        fund_a, fund_b, fund_c = self.Analytic.create(
            [
                {"name": f"Fund {name}", "plan_id": fund_plan.id}
                for name in ("A", "B", "C")
            ]
        )
        fname = fund_plan._budget_column_name()
        row_a = budget_row_key([self.costcenter1.id, fund_a.id])
        row_b = budget_row_key([self.costcenter1.id, fund_b.id])
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product1,
                    "product_qty": 4,
                    "price_unit": 250,
                    "analytic_distribution": {row_a: 60, row_b: 40},
                }
            ]
        )
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()
        line = purchase.order_line
        self.assertEqual(
            {move[fname]: move.debit for move in purchase.budget_move_ids},
            {fund_a: 600.0, fund_b: 400.0},
        )
        self.assertEqual(purchase.budget_move_ids.kpi_id, self.kpi1)
        self.assertEqual(line.amount_commit, {row_a: 600.0, row_b: 400.0})
        # A bill of 1 unit returns 60% and 40% of it to each row
        purchase.action_create_invoice()
        invoice = purchase.invoice_ids.with_context(check_move_validity=False)
        invoice.invoice_line_ids.quantity = 1
        invoice.invoice_date = invoice.date
        invoice.action_post()
        self.assertEqual(line.amount_commit, {row_a: 450.0, row_b: 300.0})
        self.assertEqual(
            {
                move[fname]: move.credit
                for move in invoice.invoice_line_ids.mapped(
                    "purchase_line_id.budget_move_ids"
                ).filtered("move_line_id")
            },
            {fund_a: 150.0, fund_b: 100.0},
        )
        self.assertAlmostEqual(self.budget_control.amount_purchase, 750.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 250.0)
        # The rows of the bill must be rows of the purchase, in any order
        purchase.action_create_invoice()
        invoice2 = (purchase.invoice_ids - invoice).with_context(
            check_move_validity=False
        )
        invoice2.invoice_date = invoice2.date
        invoice2.invoice_line_ids.analytic_distribution = {
            budget_row_key([self.costcenter1.id, fund_c.id]): 100
        }
        with self.assertRaisesRegex(UserError, "Analytic distribution mismatch"):
            invoice2.action_post()
        invoice2.invoice_line_ids.analytic_distribution = {
            f"{fund_a.id},{self.costcenter1.id}": 60,
            row_b: 40,
        }
        invoice2.action_post()
        self.assertEqual(line.amount_commit, {row_a: 0.0, row_b: 0.0})
        self.assertAlmostEqual(self.budget_control.amount_purchase, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 1000.0)

    @freeze_time("2001-02-01")
    def test_06_purchase_commit_forward(self):
        """The commitment of each row of a purchase line is carried forward to
        the next period, and back when the forward is reset to draft."""
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.budget_period.write({"control_budget": True, "control_level": "analytic"})
        fund_plan = self.AnalyticPlan.create({"name": "Fund", "control_budget": False})
        fund_a, fund_b = self.Analytic.create(
            [{"name": f"Fund {name}", "plan_id": fund_plan.id} for name in "AB"]
        )
        fname = fund_plan._budget_column_name()
        row_a = budget_row_key([self.costcenter1.id, fund_a.id])
        row_b = budget_row_key([self.costcenter1.id, fund_b.id])
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product1,
                    "product_qty": 1,
                    "price_unit": 300,
                    "analytic_distribution": {row_a: 60, row_b: 40},
                }
            ]
        )
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()
        next_period = self.env["budget.period"].create(
            {
                "name": f"Budget for FY{self.year + 1}",
                "template_id": self.template.id,
                "bm_date_from": f"{self.year + 1}-01-01",
                "bm_date_to": f"{self.year + 1}-12-31",
                "plan_date_range_type_id": self.date_range_type.id,
            }
        )
        forward = self.CommitForward.create(
            {"name": "Forward purchases", "to_budget_period_id": next_period.id}
        )
        forward.action_review_budget_commit()
        self.assertEqual(
            {line[fname]: line.amount_commit for line in forward.forward_purchase_ids},
            {fund_a: 180.0, fund_b: 120.0},
        )
        # Forward from its preview, as users do
        res = forward.preview_budget_commit_forward_info()
        info = self.env[res["res_model"]].with_context(**res["context"]).create({})
        self.assertEqual(
            [
                (info_line.analytic_account_id, info_line.initial_commit)
                for info_line in info.forward_info_line_ids
            ],
            [(self.costcenter1, 300.0)],
        )
        info.action_budget_commit_forward()
        line = purchase.order_line
        carried = line.budget_move_ids.filtered(
            lambda move: move.date >= next_period.bm_date_from
        )
        self.assertEqual(
            {move[fname]: move.debit for move in carried},
            {fund_a: 180.0, fund_b: 120.0},
        )
        self.assertAlmostEqual(self.budget_control.amount_purchase, 0.0)
        ForwardLine = self.env["budget.commit.forward.line"]
        key = (next_period.id, self.costcenter1.id)
        carried_in = ForwardLine._get_commit_forward_in_map(
            next_period.ids, self.costcenter1.ids
        )
        self.assertEqual(carried_in[key], 300.0)
        # Back to draft, the commitment is in its period again
        forward.action_draft()
        self.assertFalse(
            line.budget_move_ids.filtered(
                lambda move: move.date >= next_period.bm_date_from
            )
        )
        self.assertAlmostEqual(self.budget_control.amount_purchase, 300.0)
        carried_in = ForwardLine._get_commit_forward_in_map(
            next_period.ids, self.costcenter1.ids
        )
        self.assertEqual(carried_in[key], 0.0)
        # Bills of a carried forward commitment take its analytic distribution
        line.fwd_analytic_distribution = {row_b: 100}
        bill_line = self.env["account.move.line"].new({"purchase_line_id": line.id})
        self.assertEqual(bill_line._related_analytic_distribution(), {row_b: 100})

    @freeze_time("2001-02-01")
    def test_07_purchase_commit_forward_bill(self):
        """A bill of the next period returns the commitment carried forward
        there, row by row."""
        self.budget_control.action_submit()
        self.budget_control.action_done()
        fund_plan = self.AnalyticPlan.create({"name": "Fund", "control_budget": False})
        fund_a, fund_b = self.Analytic.create(
            [{"name": f"Fund {name}", "plan_id": fund_plan.id} for name in "AB"]
        )
        fname = fund_plan._budget_column_name()
        row_a = budget_row_key([self.costcenter1.id, fund_a.id])
        row_b = budget_row_key([self.costcenter1.id, fund_b.id])
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product1,
                    "product_qty": 1,
                    "price_unit": 300,
                    "analytic_distribution": {row_a: 60, row_b: 40},
                }
            ]
        )
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()
        next_period = self.env["budget.period"].create(
            {
                "name": f"Budget for FY{self.year + 1}",
                "template_id": self.template.id,
                "bm_date_from": f"{self.year + 1}-01-01",
                "bm_date_to": f"{self.year + 1}-12-31",
                "plan_date_range_type_id": self.date_range_type.id,
            }
        )
        forward = self.CommitForward.create(
            {"name": "Forward purchases", "to_budget_period_id": next_period.id}
        )
        forward.action_review_budget_commit()
        forward.action_budget_commit_forward()
        line = purchase.order_line
        with freeze_time(f"{self.year + 1}-02-01"):
            # The bill takes its own date to commit
            purchase = purchase.with_context(force_date_commit=False)
            purchase.action_create_invoice()
            bill = purchase.invoice_ids
            self.assertEqual(
                bill.invoice_line_ids.analytic_distribution, {row_a: 60.0, row_b: 40.0}
            )
            bill.invoice_date = bill.date
            bill.action_post()
        self.assertEqual(line.amount_commit, {row_a: 0.0, row_b: 0.0})
        returned = line.budget_move_ids.filtered("move_line_id")
        self.assertEqual(
            {move[fname]: (str(move.date), move.credit) for move in returned},
            {
                fund_a: (f"{self.year + 1}-02-01", 180.0),
                fund_b: (f"{self.year + 1}-02-01", 120.0),
            },
        )

    @freeze_time("2001-02-01")
    def test_08_purchase_forward_other_dimension(self):
        """A commitment is carried forward to other dimensions, e.g. from Fund
        A to Fund B: the bills before the forward stay on Fund A, the ones
        after it go to Fund B, and the forward is reversed only before them."""
        self.budget_control.action_submit()
        self.budget_control.action_done()
        fund_plan = self.AnalyticPlan.create({"name": "Fund", "control_budget": False})
        fund_a, fund_b = self.Analytic.create(
            [{"name": f"Fund {name}", "plan_id": fund_plan.id} for name in "AB"]
        )
        fname = fund_plan._budget_column_name()
        row_a = budget_row_key([self.costcenter1.id, fund_a.id])
        row_b = budget_row_key([self.costcenter1.id, fund_b.id])
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product1,
                    "product_qty": 3,
                    "price_unit": 100,
                    "analytic_distribution": {row_a: 100},
                }
            ]
        )
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()
        purchase = purchase.with_context(force_date_commit=False)
        line = purchase.order_line

        def bill(qty, date=None):
            purchase.action_create_invoice()
            bill = purchase.invoice_ids.filtered(lambda move: move.state == "draft")
            bill.invoice_line_ids.with_context(check_move_validity=False).quantity = qty
            bill.write({"date": date or bill.date, "invoice_date": date or bill.date})
            return bill

        # A bill before the forward stays on Fund A
        bill(1).action_post()
        self.assertEqual(line.amount_commit, {row_a: 200.0})
        next_period = self.env["budget.period"].create(
            {
                "name": f"Budget for FY{self.year + 1}",
                "template_id": self.template.id,
                "bm_date_from": f"{self.year + 1}-01-01",
                "bm_date_to": f"{self.year + 1}-12-31",
                "plan_date_range_type_id": self.date_range_type.id,
            }
        )

        def forward(name):
            forward = self.CommitForward.create(
                {"name": name, "to_budget_period_id": next_period.id}
            )
            forward.action_review_budget_commit()
            # The dimensions of the row by default, one account of each plan
            fwd_line = forward.forward_purchase_ids
            self.assertEqual(fwd_line.to_dimension_ids, fund_a)
            with self.assertRaisesRegex(ValidationError, "one account of each plan"):
                fwd_line.to_dimension_ids = fund_a | fund_b
            # Only accounts of plans without Control Budget
            with self.assertRaises(ValueError):
                fwd_line.to_dimension_ids = self.costcenterX
            fwd_line.to_dimension_ids = fund_b
            forward.action_budget_commit_forward()
            return forward

        done = forward("Forward to Fund B")
        carried = line.budget_move_ids.filtered(
            lambda move: move.date >= next_period.bm_date_from
        )
        self.assertEqual({move[fname]: move.debit for move in carried}, {fund_b: 200.0})
        self.assertEqual(line.fwd_analytic_distribution, {row_b: 100.0})
        self.assertEqual(line.amount_commit, {row_a: 0.0, row_b: 200.0})
        # Reversed while not billed in the new period, back on Fund A
        done.action_draft()
        self.assertEqual(line.amount_commit, {row_a: 200.0})
        done.unlink()
        forward_b = forward("Forward to Fund B again")
        # A bill dated before the forward would return what is no longer there
        late_bill = bill(1)
        with self.assertRaisesRegex(UserError, "is carried forward to"):
            late_bill.action_post()
        late_bill.unlink()
        # The bills of the new period go to Fund B
        with freeze_time(f"{self.year + 1}-02-01"):
            next_bill = bill(1, fields.Date.today())
            self.assertEqual(
                next_bill.invoice_line_ids.analytic_distribution, {row_b: 100.0}
            )
            next_bill.action_post()
        self.assertEqual(line.amount_commit, {row_a: 0.0, row_b: 100.0})
        with self.assertRaisesRegex(UserError, "Cannot reverse"):
            forward_b.action_draft()

    @freeze_time("2001-02-01")
    def test_09_purchase_forward_some_rows(self):
        """Forwarding one row of a purchase line keeps its other rows."""
        self.budget_control.action_submit()
        self.budget_control.action_done()
        fund_plan = self.AnalyticPlan.create({"name": "Fund", "control_budget": False})
        fund_a, fund_b, fund_c = self.Analytic.create(
            [{"name": f"Fund {name}", "plan_id": fund_plan.id} for name in "ABC"]
        )
        row_a, row_b, row_c = (
            budget_row_key([self.costcenter1.id, fund.id])
            for fund in (fund_a, fund_b, fund_c)
        )
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product1,
                    "product_qty": 1,
                    "price_unit": 300,
                    "analytic_distribution": {row_a: 60, row_b: 40},
                }
            ]
        )
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()
        line = purchase.order_line
        next_period = self.env["budget.period"].create(
            {
                "name": f"Budget for FY{self.year + 1}",
                "template_id": self.template.id,
                "bm_date_from": f"{self.year + 1}-01-01",
                "bm_date_to": f"{self.year + 1}-12-31",
                "plan_date_range_type_id": self.date_range_type.id,
            }
        )
        forward = self.CommitForward.create(
            {"name": "Forward Fund A", "to_budget_period_id": next_period.id}
        )
        forward.action_review_budget_commit()
        fwd_line_a = forward.forward_purchase_ids.filtered(
            lambda fwd_line: fwd_line.to_dimension_ids == fund_a
        )
        fwd_line_a.action_keep_only_selected()
        self.assertEqual(fwd_line_a.dimension_ids, fund_a)
        self.assertFalse(fwd_line_a.forward_changed)
        fwd_line_a.to_dimension_ids = fund_c
        self.assertTrue(fwd_line_a.forward_changed)
        forward.action_budget_commit_forward()
        self.assertEqual(line.fwd_analytic_distribution, {row_c: 60.0, row_b: 40.0})
        self.assertEqual(
            line._get_budget_rows_at(next_period.bm_date_from), {row_c, row_b}
        )
        # A next forward takes each row from its own commitment date
        later_period = self.env["budget.period"].create(
            {
                "name": f"Budget for FY{self.year + 2}",
                "template_id": self.template.id,
                "bm_date_from": f"{self.year + 2}-01-01",
                "bm_date_to": f"{self.year + 2}-12-31",
                "plan_date_range_type_id": self.date_range_type.id,
            }
        )
        later = self.CommitForward.create(
            {"name": "Forward later", "to_budget_period_id": later_period.id}
        )
        later.action_review_budget_commit()
        self.assertEqual(
            {
                fwd_line.to_dimension_ids: fwd_line.date_commit
                for fwd_line in later.forward_purchase_ids
            },
            {fund_c: next_period.bm_date_from, fund_b: line.date_commit},
        )
        later.action_draft()
        later.unlink()
        with freeze_time(f"{self.year + 1}-02-01"):
            purchase = purchase.with_context(force_date_commit=False)
            purchase.action_create_invoice()
            bill = purchase.invoice_ids
            bill.invoice_date = bill.date
            bill.action_post()
        self.assertEqual(line.amount_commit, {row_a: 0.0, row_b: 0.0, row_c: 0.0})
        # Once billed in the new period, the forward stays
        with self.assertRaisesRegex(UserError, "Cannot reverse"):
            forward.action_draft()

    @freeze_time("2001-02-01")
    def test_10_purchase_forward_twice(self):
        """A commitment forwarded to a period that does not use it is
        forwarded again, from the date it was carried to, and billed there:
        each period nets its own moves."""
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product1,
                    "product_qty": 1,
                    "price_unit": 300,
                    "analytic_distribution": {str(self.costcenter1.id): 100},
                }
            ]
        )
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()
        line = purchase.order_line
        period2, period3 = (self._create_period(self.year + n) for n in (1, 2))
        first = self._forward_commitments(period2)
        first.action_budget_commit_forward()
        second = self._forward_commitments(period3)
        self.assertEqual(second.forward_purchase_ids.date_commit, period2.bm_date_from)
        second.action_budget_commit_forward()
        self.assertEqual(
            self._get_consumptions(self.costcenter1),
            {(period3, self.costcenter1, "30_po_commit"): -300.0},
        )
        # Both forwards keep their moves flagged
        self.assertEqual(len(line.budget_move_ids.filtered("fwd_commit")), 4)
        with self.assertRaisesRegex(UserError, "Cannot reverse"):
            first.action_draft()
        self._bill_purchase(purchase, f"{self.year + 2}-02-01")
        self.assertEqual(line.amount_commit, {str(self.costcenter1.id): 0.0})
        billed = {(period3, self.costcenter1, "80_actual"): -300.0}
        self.assertEqual(self._get_consumptions(self.costcenter1), billed)
        line.recompute_budget_move()
        self.assertEqual(self._get_consumptions(self.costcenter1), billed)

    @freeze_time("2001-02-01")
    def test_11_purchase_forward_yearly_analytics(self):
        """A commitment on yearly analytics, a new one each period, is
        forwarded to the analytic each continues as, created by the
        forwards, and billed on the last one."""
        first_analytic = self.Analytic.create(
            {
                "name": "Yearly",
                "code": "YEARLY",
                "plan_id": self.aa_plan1.id,
                "budget_period_id": self.budget_period.id,
            }
        )
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product1,
                    "product_qty": 1,
                    "price_unit": 300,
                    "analytic_distribution": {str(first_analytic.id): 100},
                }
            ]
        )
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()
        Continue = self.env["budget.analytic.continue"]
        periods = [self._create_period(self.year + n) for n in (1, 2)]
        for period in periods:
            forward = self._forward_commitments(period)
            self.assertTrue(forward.missing_analytic)
            action = forward.action_continue_analytics()
            wizard = Continue.with_context(**action["context"]).create({})
            self.assertEqual(wizard.line_ids.action, "create")
            wizard.action_confirm()
            forward.action_budget_commit_forward()
        second_analytic = first_analytic.next_analytic_id
        third_analytic = second_analytic.next_analytic_id
        self.assertEqual(
            (second_analytic | third_analytic).budget_period_id,
            periods[0] | periods[1],
        )
        self.assertEqual(
            first_analytic._get_forward_analytic(periods[1]), third_analytic
        )
        line = purchase.order_line
        self.assertEqual(
            line.fwd_analytic_distribution, {str(third_analytic.id): 100.0}
        )
        analytics = first_analytic | second_analytic | third_analytic
        self.assertEqual(
            self._get_consumptions(analytics),
            {(periods[1], third_analytic, "30_po_commit"): -300.0},
        )
        bill = self._bill_purchase(purchase, f"{self.year + 2}-02-01")
        self.assertEqual(
            bill.invoice_line_ids.analytic_distribution,
            {str(third_analytic.id): 100.0},
        )
        self.assertEqual(
            self._get_consumptions(analytics),
            {(periods[1], third_analytic, "80_actual"): -300.0},
        )

    @freeze_time("2001-02-01")
    def test_12_balance_forward_carries_commitment_budget(self):
        """Once its commitments are forwarded, the balance of a period carries
        their budget too: the next period has it for them, and the preview
        warns of the commitments not forwarded yet."""
        self.budget_control.action_submit()
        self.budget_control.action_done()
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product1,
                    "product_qty": 1,
                    "price_unit": 300,
                    "analytic_distribution": {str(self.costcenter1.id): 100},
                }
            ]
        )
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()
        period2 = self._create_period(self.year + 1)
        balance = self.env["budget.balance.forward"].create(
            {
                "name": "Balance to the next period",
                "from_budget_period_id": self.budget_period.id,
                "to_budget_period_id": period2.id,
            }
        )

        def review():
            balance.action_review_budget_balance()
            res = balance.preview_budget_balance_forward_info()
            info = self.env[res["res_model"]].with_context(**res["context"]).create({})
            info_line = info.forward_info_line_ids.filtered(
                lambda info_line: info_line.analytic_account_id == self.costcenter1
            )
            return info, info_line

        # Before the commitments, the balance leaves their budget
        info, info_line = review()
        self.assertEqual(info.open_commitment, 300.0)
        self.assertEqual(info_line.initial_available, 2100.0)
        balance.action_draft()
        self._forward_commitments(period2).action_budget_commit_forward()
        info, info_line = review()
        self.assertFalse(info.open_commitment)
        self.assertEqual(
            (
                info_line.initial_available,
                info_line.initial_commit,
                info_line.amount_balance,
            ),
            (2400.0, 300.0, 2100.0),
        )
