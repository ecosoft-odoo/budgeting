# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form, tagged

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
                ex.total_amount_currency = (
                    ex_line["price_unit"] * ex_line["product_qty"]
                )
                ex.analytic_distribution = ex_line["analytic_distribution"]
                ex.activity_id = ex_line["activity_id"]
            expense = ex.save()
            expense.tax_ids = False  # test without tax
            expense_ids.append(expense.id)
        expense_sheet = self.env["hr.expense.sheet"].create(
            {
                "name": "Test Expense",
                "employee_id": user.employee_id.id,
                "expense_line_ids": [Command.set(expense_ids)],
            }
        )
        return expense_sheet

    @freeze_time("2001-02-01")
    def test_01_budget_activity_expense_analytic(self):
        """
        On expense,
        - If no activity, budget follows product's account
        - If activity is selected, account follows activity's regardless of product
        """
        self.budget_period.control_level = "analytic"
        self.assertEqual(self.budget_period.control_level, "analytic")

        analytic_distribution = {str(self.costcenter1.id): 100.0}
        expense = self._create_expense_sheet(
            [
                {
                    "product_id": self.product1,  # KPI3
                    "product_qty": 3,
                    "price_unit": 401,
                    "analytic_distribution": analytic_distribution,
                    "activity_id": self.activity3,
                },
            ]
        )
        self.assertEqual(expense.expense_line_ids.account_id, self.account_kpi3)

        # Change Product, account will not change (following activity only)
        with Form(expense.expense_line_ids[:1]) as ex:
            ex.product_id = self.product2
        ex.save()
        self.assertEqual(expense.expense_line_ids.account_id, self.account_kpi3)
        # After change product, taxes will recompute. we need test without tax
        self.assertTrue(expense.expense_line_ids.tax_ids)
        expense.expense_line_ids.tax_ids = False
        expense = expense.with_context(force_date_commit=expense.expense_line_ids.date)
        # Can commit budget because control level analytic (2400.0)
        expense.action_submit_sheet()
        expense.action_approve_expense_sheets()

        # Check move must have activity in line
        move = expense.account_move_ids
        # EX Commit = 1203.0, INV Actual = 0.0, Balance = 1197.0
        self.assertAlmostEqual(self.budget_control.amount_expense, 1203.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 1197.0)
        self.assertEqual(
            expense.budget_move_ids.account_id,
            expense.expense_line_ids.activity_id.account_id,
        )
        self.assertEqual(
            expense.budget_move_ids.activity_id,
            expense.expense_line_ids.activity_id,
        )
        self.assertEqual(move.invoice_line_ids.activity_id, self.activity3)

        # post invoice
        expense.action_sheet_move_post()

        # EX Commit = 0.0, INV Actual = 1203.0, Balance = 1197.0
        self.assertAlmostEqual(self.budget_control.amount_expense, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 1203.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 1197.0)
        self.assertEqual(
            move.budget_move_ids.account_id,
            move.invoice_line_ids.activity_id.account_id,
        )
        self.assertEqual(
            move.budget_move_ids.activity_id,
            move.invoice_line_ids.activity_id,
        )
        self.assertEqual(move.invoice_line_ids.activity_id, self.activity3)

    @freeze_time("2001-02-01")
    def test_02_budget_activity_expense_analytic_kpi(self):
        """
        On expense,
        - If no activity, budget follows product's account
        - If activity is selected, account follows activity's regardless of product
        """
        self.budget_period.control_level = "analytic_kpi"
        self.assertEqual(self.budget_period.control_level, "analytic_kpi")

        analytic_distribution = {str(self.costcenter1.id): 100.0}
        expense = self._create_expense_sheet(
            [
                {
                    "product_id": self.product1,  # KPI3
                    "product_qty": 3,
                    "price_unit": 401,
                    "analytic_distribution": analytic_distribution,
                    "activity_id": self.activity3,
                },
            ]
        )
        self.assertEqual(expense.expense_line_ids.account_id, self.account_kpi3)

        expense = expense.with_context(force_date_commit=expense.expense_line_ids.date)
        # Can't commit budget because control level analytic&kpi (1200.0)
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            expense.action_submit_sheet()
        expense.action_reset_expense_sheets()

        expense.expense_line_ids.total_amount = 400.0
        expense.action_submit_sheet()
        expense.action_approve_expense_sheets()

        # Check move must have activity in line
        move = expense.account_move_ids
        # EX Commit = 400.0, INV Actual = 0.0, Balance = 2000.0
        self.assertAlmostEqual(self.budget_control.amount_expense, 400.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2000.0)
        self.assertEqual(
            expense.budget_move_ids.account_id,
            expense.expense_line_ids.activity_id.account_id,
        )
        self.assertEqual(
            expense.budget_move_ids.activity_id,
            expense.expense_line_ids.activity_id,
        )
        self.assertEqual(move.invoice_line_ids.activity_id, self.activity3)

        # post invoice
        expense.action_sheet_move_post()

        # EX Commit = 0.0, INV Actual = 400.0, Balance = 2000.0
        self.assertAlmostEqual(self.budget_control.amount_expense, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 400.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2000.0)
        self.assertEqual(
            move.budget_move_ids.account_id,
            move.invoice_line_ids.activity_id.account_id,
        )
        self.assertEqual(
            move.budget_move_ids.activity_id,
            move.invoice_line_ids.activity_id,
        )
        self.assertEqual(move.invoice_line_ids.activity_id, self.activity3)
