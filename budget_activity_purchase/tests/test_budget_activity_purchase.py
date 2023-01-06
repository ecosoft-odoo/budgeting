# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from freezegun import freeze_time

from odoo.tests import tagged
from odoo.tests.common import Form

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
                    line.account_analytic_id = po_line["analytic_id"]
        purchase = po.save()
        return purchase

    @freeze_time("2001-02-01")
    def test_01_budget_activity_purchase(self):
        """
        On purchase,
        - If no activity, budget follows product's account
        - If activity is selected, account follows activity's regardless of product
        """
        # Control budget
        self.budget_period.control_budget = True
        self.budget_control.action_done()

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
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()
        # Check if not selected activity, budget move will get account from product
        fpos = purchase.fiscal_position_id
        self.assertEqual(
            purchase.budget_move_ids.account_id,
            purchase.order_line.product_id.product_tmpl_id.get_product_accounts(fpos)[
                "expense"
            ],
        )
        # PO Commit = 30, INV Actual = 0, Balance = 270
        self.assertEqual(self.budget_control.amount_commit, 30)
        self.assertEqual(self.budget_control.amount_actual, 0)
        self.assertEqual(self.budget_control.amount_balance, 2370)

        purchase.button_cancel()
        purchase.button_draft()
        # Add activity in order line
        purchase.order_line.activity_id = self.activity3.id
        purchase.button_confirm()
        self.assertEqual(
            purchase.budget_move_ids.account_id,
            purchase.order_line.activity_id.account_id,
        )

        # Create and post invoice
        purchase.action_create_invoice()
        self.assertEqual(purchase.invoice_status, "invoiced")
        invoice = purchase.invoice_ids[:1]
        # Check activity in invoice line must be equal purchase line
        self.assertEqual(
            invoice.invoice_line_ids.activity_id, purchase.order_line.activity_id
        )
