# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.budget_control.tests.common import BudgetControlCommon


@tagged("post_install", "-at_install")
class TestBudgetControl(BudgetControlCommon):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        BudgetActivity = cls.env["budget.activity"]  # Create sample activity
        cls.activity1 = BudgetActivity.create(
            {"name": "Activity 1", "account_id": cls.account_kpi1.id}
        )
        cls.activity2 = BudgetActivity.create(
            {"name": "Activity 2", "account_id": cls.account_kpi2.id}
        )

    @freeze_time("2001-02-01")
    def test_01_budget_activity_account(self):
        """
        On vendor bill,
        - If no activity, budget follows product's account
        - If activity is selected, account follows activity's regardless of product
        - User can always change account code afterwards
        - Posting invoice, will create budget move with activity
        """
        self.budget_period.account = False
        invoice = self._create_simple_bill(self.costcenter1, self.account_kpi1, 10)
        # Change to product2, account should change to account_kpi2
        with Form(invoice) as invoice_form:
            with invoice_form.invoice_line_ids.edit(0) as line_form:
                line_form.product_id = self.product2
                line_form.price_unit = 10  # Change product, amount will reset
        invoice_form.save()
        self.assertEqual(self.account_kpi2, invoice.invoice_line_ids[0].account_id)
        # Set activity1, account should change to account_kpi1
        with Form(invoice) as invoice_form:
            with invoice_form.invoice_line_ids.edit(0) as line_form:
                line_form.activity_id = self.activity1
        invoice_form.save()
        self.assertEqual(self.account_kpi1, invoice.invoice_line_ids[0].account_id)
        # Set account only to account_kpi3
        with Form(invoice) as invoice_form:
            with invoice_form.invoice_line_ids.edit(0) as line_form:
                line_form.account_id = self.account_kpi3
        invoice_form.save()
        # Invoice line is not set up as following,
        self.assertEqual(self.account_kpi3, invoice.invoice_line_ids[0].account_id)
        self.assertEqual(self.product2, invoice.invoice_line_ids[0].product_id)
        self.assertEqual(self.activity1, invoice.invoice_line_ids[0].activity_id)
        with self.assertRaises(UserError):
            invoice.action_post()  # Account in Activity and Account is not equal.
        # Reset state and set account = account in activity
        invoice.invoice_line_ids[0].account_id = self.activity1.account_id
        invoice.state = "draft"
        # All values will be passed to budget move
        invoice.action_post()
        self.assertEqual(self.account_kpi1, invoice.budget_move_ids[0].account_id)
        self.assertEqual(self.product2, invoice.budget_move_ids[0].product_id)
        self.assertEqual(self.activity1, invoice.budget_move_ids[0].activity_id)
