# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.budget_control.tests.common import BudgetControlCommon


@tagged("post_install", "-at_install")
class TestBudgetActivity(BudgetControlCommon):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        BudgetActivity = cls.env["budget.activity"]  # Create sample activity
        cls.env.company.budget_control_key = "activity_id"  # Control by activity
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

        # Create budget plan
        lines = [
            Command.create(
                {"analytic_account_id": cls.costcenter1.id, "amount": 2400.0}
            )
        ]
        cls.budget_plan = cls.create_budget_plan(
            cls,
            name="Test - Plan {cls.budget_period.name}",
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

        # Control budget
        cls.budget_period.control_budget = True
        cls.budget_control.action_submit()
        cls.budget_control.action_done()

    def _create_simple_bill_activity(self, analytic_distribution, activity, amount):
        invoice = self.Move.create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "invoice_date": datetime.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "quantity": 1,
                            "activity_id": activity.id,
                            "price_unit": amount,
                            "analytic_distribution": analytic_distribution,
                        },
                    )
                ],
            }
        )
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
        analytic_distribution = {self.costcenter1.id: 100}
        price_unit = 10.0

        bill1 = self._create_simple_bill_activity(
            analytic_distribution, self.activity1, price_unit
        )
        self.assertEqual(
            self.activity1.account_id, bill1.invoice_line_ids[0].account_id
        )
        # Change to product2, account should not change.
        with Form(bill1) as invoice_form:
            with invoice_form.invoice_line_ids.edit(0) as line_form:
                line_form.product_id = self.product2
                line_form.price_unit = price_unit  # Change product, amount will reset
        invoice_form.save()
        self.assertEqual(
            self.activity1.account_id, bill1.invoice_line_ids[0].account_id
        )
        self.assertEqual(self.product2, bill1.invoice_line_ids[0].product_id)
        self.assertEqual(self.activity1, bill1.invoice_line_ids[0].activity_id)

        # Change activity on template line for test no activity in template line
        # It should errors `not valid in template`
        with Form(self.template_line1) as line:
            line.kpi_id = self.kpi2
        with self.assertRaisesRegex(UserError, "not valid in template"):
            bill1.action_post()
        bill1.button_draft()

        # Change activity on template line for test multi activity in template line
        with Form(self.template_line1) as line:
            line.kpi_id = self.kpi1
        with Form(self.template_line2) as line:
            line.kpi_id = self.kpi1
        with self.assertRaisesRegex(
            UserError,
            "Template Lines has more than one KPI being referenced by the same",
        ):
            bill1.action_post()
        bill1.button_draft()

        # Change back to basic
        with Form(self.template_line2) as line:
            line.kpi_id = self.kpi2
        # Reset state and set account = account in activity
        bill1.invoice_line_ids[0].account_id = self.activity1.account_id
        # All values will be passed to budget move
        bill1.action_post()
        self.assertEqual(self.account_kpi1, bill1.budget_move_ids[0].account_id)
        self.assertEqual(self.product2, bill1.budget_move_ids[0].product_id)
        self.assertEqual(self.activity1, bill1.budget_move_ids[0].activity_id)

        # Check budget move must account equal accuont in activity
        with self.assertRaisesRegex(
            UserError, "Account not equal to Activity's Account"
        ):
            bill1.budget_move_ids[0].account_id = self.account_kpi3.id

        # Check change account in activity, after commit. it should not allow
        with self.assertRaisesRegex(
            UserError,
            "You cannot change the account because it is already used in a commit.",
        ):
            with Form(self.activity1) as activity:
                activity.account_id = self.account_kpi2

    @freeze_time("2001-02-01")
    def test_02_budget_adjustment_activity(self):
        """
        On budget adjustment,
        - If no activity, budget follows product's account
        - If activity is selected, account follows activity's regardless of product
        - User can always change account code afterwards
        """
        self.assertEqual(self.budget_control.amount_balance, 2400.0)
        budget_adjust = self.BudgetAdjust.create(
            {
                "date_commit": "2001-02-01",
            }
        )
        with Form(budget_adjust.adjust_item_ids) as line:
            line.adjust_id = budget_adjust
            line.adjust_type = "consume"
            line.product_id = self.product1
            line.analytic_distribution = {self.costcenter1.id: 100}
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
