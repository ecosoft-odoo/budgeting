# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.budget_activity.tests.test_budget_activity import TestBudgetActivity


@tagged("post_install", "-at_install")
class TestBudgetActivityPurchase(TestBudgetActivity):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        cls.product1.product_tmpl_id.purchase_method = "purchase"

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
                    line.activity_id = po_line["activity_id"]
        purchase = po.save()
        return purchase

    @freeze_time("2001-02-01")
    def test_01_budget_activity_purchase_control_analytic(self):
        """
        On purchase,
        - If no activity, budget follows product's account
        - If activity is selected, account follows activity's regardless of product
        """
        self.budget_period.control_level = "analytic"
        self.assertEqual(self.budget_period.control_level, "analytic")
        analytic_distribution = {str(self.costcenter1.id): 100.0}
        # KPI1=400, KPI2=800, KPI3=1,200
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product1,  # KPI3 = 1203.0
                    "product_qty": 3,
                    "price_unit": 401,
                    "analytic_distribution": analytic_distribution,
                    "activity_id": self.activity3,
                },
            ]
        )
        purchase = purchase.with_context(force_date_commit=purchase.date_order)

        # Can commit budget because control level analytic (2400.0)
        purchase.button_confirm()

        # PO Commit = 1203.0, INV Actual = 0.0, Balance = 1197.0
        self.assertAlmostEqual(self.budget_control.amount_purchase, 1203.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 1197.0)
        self.assertEqual(
            purchase.budget_move_ids.account_id,
            purchase.order_line.activity_id.account_id,
        )
        self.assertEqual(
            purchase.budget_move_ids.activity_id,
            purchase.order_line.activity_id,
        )

        # Create and post invoice
        purchase.action_create_invoice()
        self.assertEqual(purchase.invoice_status, "invoiced")
        invoice = purchase.invoice_ids[:1]
        # Check activity in invoice line must be equal purchase line
        self.assertEqual(
            invoice.invoice_line_ids.activity_id, purchase.order_line.activity_id
        )

        invoice.invoice_date = invoice.date
        invoice.action_post()

        # PO Commit = 0.0, INV Actual = 1203.0, Balance = 1197.0
        self.assertAlmostEqual(self.budget_control.amount_purchase, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 1203.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 1197.0)
        self.assertEqual(
            invoice.budget_move_ids.account_id,
            invoice.invoice_line_ids.activity_id.account_id,
        )
        self.assertEqual(
            invoice.budget_move_ids.activity_id,
            invoice.invoice_line_ids.activity_id,
        )

    @freeze_time("2001-02-01")
    def test_02_budget_activity_purchase_control_analytic_kpi(self):
        """
        On purchase,
        - If no activity, budget follows product's account
        - If activity is selected, account follows activity's regardless of product
        """
        self.budget_period.control_level = "analytic_kpi"
        self.assertEqual(self.budget_period.control_level, "analytic_kpi")
        analytic_distribution = {str(self.costcenter1.id): 100.0}
        # KPI1=400, KPI2=800, KPI3=1,200
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product1,  # KPI3 = 1203.0
                    "product_qty": 3,
                    "price_unit": 401,
                    "analytic_distribution": analytic_distribution,
                    "activity_id": self.activity3,
                },
            ]
        )
        purchase = purchase.with_context(force_date_commit=purchase.date_order)

        # Can't commit budget because control level analytic&kpi (1200.0)
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            purchase.button_confirm()
        purchase.button_draft()

        purchase.order_line.price_unit = 200.0
        purchase.button_confirm()
        # PO Commit = 600.0, INV Actual = 0.0, Balance = 1800.0
        self.assertAlmostEqual(self.budget_control.amount_purchase, 600.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 1800.0)
        self.assertEqual(
            purchase.budget_move_ids.account_id,
            purchase.order_line.activity_id.account_id,
        )
        self.assertEqual(
            purchase.budget_move_ids.activity_id,
            purchase.order_line.activity_id,
        )

        # Create and post invoice
        purchase.action_create_invoice()
        self.assertEqual(purchase.invoice_status, "invoiced")
        invoice = purchase.invoice_ids[:1]
        # Check activity in invoice line must be equal purchase line
        self.assertEqual(
            invoice.invoice_line_ids.activity_id, purchase.order_line.activity_id
        )

        invoice.invoice_date = invoice.date
        invoice.action_post()

        # PO Commit = 0.0, INV Actual = 600.0, Balance = 1800.0
        self.assertAlmostEqual(self.budget_control.amount_purchase, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 600.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 1800.0)
        self.assertEqual(
            invoice.budget_move_ids.account_id,
            invoice.invoice_line_ids.activity_id.account_id,
        )
        self.assertEqual(
            invoice.budget_move_ids.activity_id,
            invoice.invoice_line_ids.activity_id,
        )
