# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.budget_activity.tests.test_budget_activity import TestBudgetActivity


@tagged("post_install", "-at_install")
class TestBudgetActivityExpense(TestBudgetActivity):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()

    @freeze_time("2001-02-01")
    def _create_expense_sheet(self, ex_lines):
        Expense = self.env["hr.expense"]
        view_id = "hr_expense.hr_expense_view_form"
        expense_ids = []
        user = self.env.ref("base.user_admin")
        for ex_line in ex_lines:
            with Form(Expense, view=view_id) as ex:
                ex.employee_id = user.employee_id
                ex.product_id = ex_line["product_id"]
                ex.quantity = ex_line["product_qty"]
                ex.unit_amount = ex_line["price_unit"]
                ex.analytic_account_id = ex_line["analytic_id"]
                ex.activity_id = ex_line["activity_id"]
            expense = ex.save()
            expense_ids.append(expense.id)
        expense_sheet = self.env["hr.expense.sheet"].create(
            {
                "name": "Test Expense",
                "employee_id": user.employee_id.id,
                "expense_line_ids": [(6, 0, expense_ids)],
            }
        )
        return expense_sheet

    @freeze_time("2001-02-01")
    def test_01_budget_activity_expense(self):
        """
        On expense,
        - If no activity, budget follows product's account
        - If activity is selected, account follows activity's regardless of product
        """
        # Control budget
        self.budget_period.control_budget = True
        self.budget_control.action_done()

        expense = self._create_expense_sheet(
            [
                {
                    "product_id": self.product1,  # KPI1
                    "product_qty": 3,
                    "price_unit": 10,
                    "analytic_id": self.costcenter1,
                    "activity_id": self.activity3,
                },
            ]
        )
        self.assertEqual(expense.expense_line_ids[:1].account_id, self.account_kpi3)
        # Change Product, account will not change (following activity only)
        with Form(expense.expense_line_ids[:1]) as ex:
            ex.product_id = self.product2
        ex.save()
        self.assertEqual(expense.expense_line_ids[:1].account_id, self.account_kpi3)
        expense = expense.with_context(
            force_date_commit=expense.expense_line_ids[:1].date
        )
        expense.action_submit_sheet()
        expense.approve_expense_sheets()
        # Create and post invoice
        expense.action_sheet_move_create()
        # Check move must have activity in line
        move = expense.account_move_id
        self.assertEqual(move.line_ids.mapped("activity_id"), self.activity3)
