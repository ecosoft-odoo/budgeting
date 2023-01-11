# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.budget_control.tests.common import BudgetControlCommon


@tagged("post_install", "-at_install")
class TestBudgetActivity(BudgetControlCommon):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        BudgetActivity = cls.env["budget.activity"]  # Create sample activity
        cls.activity1 = BudgetActivity.create(
            {
                "name": "Activity 1",
                "kpi_id": cls.kpi1.id,
                "account_id": cls.account_kpi1.id,
            }
        )
        cls.activity2 = BudgetActivity.create(
            {
                "name": "Activity 2",
                "kpi_id": cls.kpi2.id,
                "account_id": cls.account_kpi2.id,
            }
        )
        cls.activity3 = BudgetActivity.create(
            {
                "name": "Activity 3",
                "kpi_id": cls.kpi3.id,
                "account_id": cls.account_kpi3.id,
            }
        )
        # Add activity on template line
        with Form(cls.template_line1) as line:
            line.kpi_id = cls.kpi1
        with Form(cls.template_line2) as line:
            line.kpi_id = cls.kpi2
        with Form(cls.template_line3) as line:
            line.kpi_id = cls.kpi3
        # Create sample ready to use Budget Control
        cls.budget_control = cls.BudgetControl.create(
            {
                "name": "CostCenter1/%s" % cls.year,
                "template_id": cls.budget_period.template_id.id,
                "budget_period_id": cls.budget_period.id,
                "analytic_account_id": cls.costcenter1.id,
                "plan_date_range_type_id": cls.date_range_type.id,
                "allocated_amount": 2400.0,
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

    def _create_simple_bill_activity(self, analytic, activity, account, amount):
        Invoice = self.env["account.move"]
        view_id = "account.view_move_form"
        with Form(
            Invoice.with_context(default_move_type="in_invoice"), view=view_id
        ) as inv:
            inv.partner_id = self.vendor
            inv.invoice_date = datetime.today()
            with inv.invoice_line_ids.new() as line:
                line.quantity = 1
                line.account_id = account
                line.price_unit = amount
                line.analytic_account_id = analytic
                line.activity_id = activity  # required when select analytic account
        invoice = inv.save()
        return invoice

    @freeze_time("2001-02-01")
    def test_01_budget_activity_account(self):
        """
        On vendor bill,
        - If no activity, budget follows product's account
        - If activity is selected, account follows activity's regardless of product
        - User can always change account code afterwards
        - Posting invoice, will create budget move with activity
        """
        # Control budget
        self.budget_period.control_budget = True
        self.budget_control.action_done()
        price_unit = 10.0
        invoice = self._create_simple_bill_activity(
            self.costcenter1, self.activity1, self.account_kpi1, price_unit
        )
        self.assertEqual(
            self.activity1.account_id, invoice.invoice_line_ids[0].account_id
        )
        # Change to product2, account should not change.
        with Form(invoice) as invoice_form:
            with invoice_form.invoice_line_ids.edit(0) as line_form:
                line_form.product_id = self.product2
                line_form.price_unit = price_unit  # Change product, amount will reset
        invoice_form.save()
        self.assertEqual(
            self.activity1.account_id, invoice.invoice_line_ids[0].account_id
        )

        # Invoice line is not set up as following,
        self.assertEqual(
            self.activity1.account_id, invoice.invoice_line_ids[0].account_id
        )
        self.assertEqual(self.product2, invoice.invoice_line_ids[0].product_id)
        self.assertEqual(self.activity1, invoice.invoice_line_ids[0].activity_id)
        # Change activity on template line for test no activity in template line
        with Form(self.template_line1) as line:
            line.kpi_id = self.kpi2
        with self.assertRaises(UserError):
            invoice.action_post()
        # Change activity on template line for test multi activity in template line
        with Form(self.template_line1) as line:
            line.kpi_id = self.kpi1
        with Form(self.template_line2) as line:
            line.kpi_id = self.kpi1
        with self.assertRaises(UserError):
            invoice.action_post()
        # Change back to basic
        with Form(self.template_line2) as line:
            line.kpi_id = self.kpi2
        # Reset state and set account = account in activity
        invoice.invoice_line_ids[0].account_id = self.activity1.account_id
        # All values will be passed to budget move
        invoice.action_post()
        self.assertEqual(self.account_kpi1, invoice.budget_move_ids[0].account_id)
        self.assertEqual(self.product2, invoice.budget_move_ids[0].product_id)
        self.assertEqual(self.activity1, invoice.budget_move_ids[0].activity_id)
        # Check budget move must account equal accuont in activity
        with self.assertRaises(UserError):
            invoice.budget_move_ids[0].account_id = self.account_kpi3.id

    @freeze_time("2001-02-01")
    def test_02_budget_adjustment_activity(self):
        """
        On budget adjustment,
        - If no activity, budget follows product's account
        - If activity is selected, account follows activity's regardless of product
        - User can always change account code afterwards
        """
        self.assertEqual(self.budget_control.amount_balance, 2400.0)
        budget_adjust = self.env["budget.move.adjustment"].create(
            {
                "date_commit": "2001-02-01",
            }
        )
        with Form(budget_adjust.adjust_item_ids) as line:
            line.adjust_id = budget_adjust
            line.adjust_type = "consume"
            line.product_id = self.product1
            line.analytic_account_id = self.costcenter1
            line.amount = 100.0
        adjust_line = line.save()
        self.assertEqual(adjust_line.account_id, self.account_kpi1)
        # Change to activity2, account should change to account_kpi2
        with Form(adjust_line) as line:
            line.activity_id = self.activity2
        self.assertEqual(adjust_line.account_id, self.activity2.account_id)
        # balance in budget control must be 'Decrease'
        budget_adjust.action_adjust()
        self.assertEqual(self.budget_control.amount_balance, 2300.0)
