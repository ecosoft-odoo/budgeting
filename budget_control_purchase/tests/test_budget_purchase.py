# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.budget_control.tests.common import BudgetControlCommon


@tagged("post_install", "-at_install")
class TestBudgetControlPurchase(BudgetControlCommon):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        # Create sample ready to use Budget Control
        cls.budget_control = cls.BudgetControl.create(
            {
                "name": "CostCenter1/%s" % cls.year,
                "template_id": cls.budget_period.template_id.id,
                "budget_period_id": cls.budget_period.id,
                "analytic_account_id": cls.costcenter1.id,
                "plan_date_range_type_id": cls.date_range_type.id,
                "template_line_ids": [
                    cls.template_line1.id,
                    cls.template_line2.id,
                    cls.template_line3.id,
                ],
            }
        )
        # Test item created for 3 kpi x 4 quarters = 12 budget items
        cls.budget_control.prepare_budget_control_matrix()
        assert len(cls.budget_control.line_ids) == 12
        # Assign budget.control amount: KPI1 = 100, KPI2=200, Total=300
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi1)[:1].write(
            {"amount": 100}
        )
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi2)[:1].write(
            {"amount": 200}
        )
        cls.budget_control.flush()  # Need to flush data into table, so it can be sql
        cls.budget_control.allocated_amount = 300
        cls.budget_control.action_done()
        # Purchase method
        cls.product1.product_tmpl_id.purchase_method = "purchase"
        cls.product2.product_tmpl_id.purchase_method = "purchase"

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
                    line.account_analytic_id = po_line["analytic_id"]
        purchase = po.save()
        return purchase

    @freeze_time("2001-02-01")
    def test_01_budget_purchase(self):
        """
        On Purchase Order
        (1) Test case, no budget check -> OK
        (2) Check Budget with analytic_kpi -> Error amount exceed on kpi1
        (3) Check Budget with analytic -> OK
        (2) Check Budget with analytic -> Error amount exceed
        """
        # KPI1 = 100, KPI2 = 200, Total = 300
        self.assertEqual(300, self.budget_control.amount_budget)
        # Prepare PO
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product1,  # KPI1 = 101 -> error
                    "product_qty": 1,
                    "price_unit": 101,
                    "analytic_id": self.costcenter1,
                },
                {
                    "product_id": self.product2,  # KPI2 = 198
                    "product_qty": 2,
                    "price_unit": 99,
                    "analytic_id": self.costcenter1,
                },
            ]
        )

        # (1) No budget check first
        self.budget_period.control_budget = False
        self.budget_period.control_level = "analytic_kpi"
        # force date commit, as freeze_time not work for write_date
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()  # No budget check no error
        # (2) Check Budget with analytic_kpi -> Error
        purchase.button_cancel()
        purchase.button_draft()
        self.budget_period.control_budget = True  # Set to check budget
        # kpi 1 (kpi1) & CostCenter1, will result in $ -1.00
        with self.assertRaises(UserError):
            purchase.button_confirm()
        # (3) Check Budget with analytic -> OK
        purchase.button_cancel()
        purchase.button_draft()
        self.budget_period.control_level = "analytic"
        purchase.button_confirm()
        self.assertEqual(self.budget_control.amount_balance, 1)
        purchase.button_cancel()
        self.assertEqual(self.budget_control.amount_balance, 300)
        # (4) Amount exceed -> Error
        purchase.order_line[1].price_unit = 100
        purchase.button_draft()
        # CostCenter1, will result in $ -1.00
        with self.assertRaises(UserError):
            purchase.button_confirm()

    @freeze_time("2001-02-01")
    def test_02_budget_purchase_to_invoice(self):
        """Purchase to Invoice, commit and uncommit"""
        # KPI1 = 100, KPI2 = 200, Total = 300
        self.assertEqual(300, self.budget_control.amount_budget)
        # Prepare PO on kpi1 with qty 3 and unit_price 10
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product1,  # KPI1 = 30
                    "product_qty": 3,
                    "price_unit": 10,
                    "analytic_id": self.costcenter1,
                },
            ]
        )
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()
        # PO Commit = 30, INV Actual = 0, Balance = 270
        self.assertEqual(self.budget_control.amount_commit, 30)
        self.assertEqual(self.budget_control.amount_actual, 0)
        self.assertEqual(self.budget_control.amount_balance, 270)
        # Create and post invoice
        purchase.action_create_invoice()
        self.assertEqual(purchase.invoice_status, "invoiced")
        invoice = purchase.invoice_ids[:1]
        # Change qty to 1
        invoice.with_context(check_move_validity=False).invoice_line_ids[0].quantity = 1
        invoice.with_context(check_move_validity=False)._onchange_invoice_line_ids()
        invoice.invoice_date = invoice.date
        invoice.action_post()
        # PO Commit = 20, INV Actual = 10, Balance = 270
        self.budget_control.invalidate_cache()
        self.assertEqual(self.budget_control.amount_commit, 20)
        self.assertEqual(self.budget_control.amount_actual, 10)
        self.assertEqual(self.budget_control.amount_balance, 270)
        # # Cancel invoice
        invoice.button_cancel()
        self.budget_control.invalidate_cache()
        self.assertEqual(self.budget_control.amount_commit, 30)
        self.assertEqual(self.budget_control.amount_actual, 0)
        self.assertEqual(self.budget_control.amount_balance, 270)

    @freeze_time("2001-02-01")
    def test_03_budget_recompute_and_close_budget_move(self):
        """Purchase to Invoice (partial)
        - Test recompute on both Purchase and Invoice
        - Test close on both Purchase and Invoice"""
        # Prepare PO on kpi1 with qty 3 and unit_price 10
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product1,  # KPI1 = 30
                    "product_qty": 2,
                    "price_unit": 15,
                    "analytic_id": self.costcenter1,
                },
                {
                    "product_id": self.product2,  # KPI2 = 40
                    "product_qty": 4,
                    "price_unit": 10,
                    "analytic_id": self.costcenter1,
                },
            ]
        )
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()
        # PO Commit = 70, INV Actual = 0
        self.assertEqual(self.budget_control.amount_purchase, 70)
        self.assertEqual(self.budget_control.amount_actual, 0)
        # Create and post invoice
        purchase.action_create_invoice()
        self.assertEqual(purchase.invoice_status, "invoiced")
        invoice = purchase.invoice_ids[:1]
        # Change qty to 1 and 3
        invoice = invoice.with_context(check_move_validity=False)
        invoice.invoice_line_ids[0].quantity = 1
        invoice.invoice_line_ids[1].quantity = 3
        invoice._onchange_invoice_line_ids()
        invoice.invoice_date = invoice.date
        invoice.action_post()
        # PO Commit = 25, INV Actual = 45
        self.budget_control.flush()
        self.assertEqual(self.budget_control.amount_purchase, 25)
        self.assertEqual(self.budget_control.amount_actual, 45)
        # Test recompute, must be same
        purchase.recompute_budget_move()
        self.budget_control.flush()
        self.assertEqual(self.budget_control.amount_purchase, 25)
        self.assertEqual(self.budget_control.amount_actual, 45)
        invoice.recompute_budget_move()
        self.budget_control.flush()
        self.assertEqual(self.budget_control.amount_actual, 45)
        self.assertEqual(self.budget_control.amount_purchase, 25)
        # Test close budget move
        purchase.close_budget_move()
        self.budget_control.flush()
        self.budget_control.invalidate_cache()
        self.assertEqual(self.budget_control.amount_purchase, 0)
        self.assertEqual(self.budget_control.amount_actual, 45)
        # Test close budget move
        invoice.close_budget_move()
        self.budget_control.flush()
        self.budget_control.invalidate_cache()
        self.assertEqual(self.budget_control.amount_purchase, 0)
        self.assertEqual(self.budget_control.amount_actual, 0)

    @freeze_time("2001-02-01")
    def test_04_balance_forward_after_commit_forward(self):
        """At year end, the budget officer forwards the open purchase
        commitments, including one carried in from last year, and then the
        balance. The balance forwarded is the one the monitoring shows."""
        BudgetPeriod = self.env["budget.period"]
        period_vals = {
            "template_id": self.budget_period.template_id.id,
            "plan_date_range_type_id": self.date_range_type.id,
            "control_level": "analytic",
            "purchase": True,
        }
        prev_year, next_year = self.year - 1, self.year + 1
        prev_period = BudgetPeriod.create(
            dict(
                period_vals,
                name="Budget for FY%s" % prev_year,
                bm_date_from="%s-01-01" % prev_year,
                bm_date_to="%s-12-31" % prev_year,
            )
        )
        next_period = BudgetPeriod.create(
            dict(
                period_vals,
                name="Budget for FY%s" % next_year,
                bm_date_from="%s-01-01" % next_year,
                bm_date_to="%s-12-31" % next_year,
            )
        )
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        # Last year PO of 40, still open, is forwarded into this year
        po_prev = self._create_purchase(
            [
                {
                    "product_id": self.product1,
                    "product_qty": 1,
                    "price_unit": 40,
                    "analytic_id": self.costcenter1,
                }
            ]
        )
        # Last year has no budget control sheet here, skip its check
        po_prev.with_context(
            force_date_commit=prev_period.bm_date_from,
            force_no_budget_check=True,
        ).button_confirm()
        self._forward_commit(self.budget_period)
        self._refresh_balance()
        self.assertEqual(self.budget_control.amount_balance, 260)
        # This year PO of 70
        po = self._create_purchase(
            [
                {
                    "product_id": self.product2,
                    "product_qty": 1,
                    "price_unit": 70,
                    "analytic_id": self.costcenter1,
                }
            ]
        )
        po.with_context(force_date_commit=po.date_order).button_confirm()
        self._refresh_balance()
        self.assertEqual(self.budget_control.amount_balance, 190)
        # Previewing the balance forward first warns of the open commitments,
        # so the officer discards it
        balance_forward = self._review_balance_forward(next_period)
        preview = balance_forward.preview_budget_balance_forward_info()
        self.assertEqual(preview["context"]["default_open_commitment"], 110)
        balance_forward.unlink()
        # Both POs are forwarded, the year gets their budget back
        self._forward_commit(next_period)
        self._refresh_balance()
        self.assertEqual(self.budget_control.amount_balance, 300)
        # The balance forward now carries what the monitoring shows
        balance_forward = self._review_balance_forward(next_period)
        line = balance_forward.forward_line_ids
        self.assertEqual(line.amount_balance, 300)
        self.assertEqual(line.amount_balance_forward, 300)
        preview = balance_forward.preview_budget_balance_forward_info()
        self.assertEqual(preview["context"]["default_open_commitment"], 0)
        balance_forward.action_budget_balance_forward()
        self.assertEqual(balance_forward.state, "done")

    def _refresh_balance(self):
        # Monitoring is an SQL view of the budget moves
        self.budget_control.flush()
        self.budget_control.invalidate_cache()

    def _review_balance_forward(self, to_period):
        forward = self.env["budget.balance.forward"].create(
            {
                "name": "Balance Forward %s" % to_period.name,
                "from_budget_period_id": self.budget_period.id,
                "to_budget_period_id": to_period.id,
            }
        )
        forward.action_review_budget_balance()
        return forward

    def _forward_commit(self, to_period):
        forward = self.env["budget.commit.forward"].create(
            {
                "name": "Commit Forward %s" % to_period.name,
                "to_budget_period_id": to_period.id,
                "purchase": True,
            }
        )
        forward.action_review_budget_commit()
        forward.action_budget_commit_forward()
        return forward
