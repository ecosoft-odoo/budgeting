# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.budget_control_request_document.tests.test_budget_control_request_document import (  # noqa: E501
    TestBudgetControlRequest,
)


@tagged("post_install", "-at_install")
class TestBudgetControlRequestExpense(TestBudgetControlRequest):
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
    def test_01_budget_request_commit_budget_expense(self):
        """Request commit to expense document"""
        # Controlled budget
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        self.assertTrue(self.budget_period.request_document)
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)

        # Prepare Request
        analytic_distribution = {self.costcenter1.id: 100}
        request_order = self.request_obj.create(
            {"line_ids": [Command.create({"request_type": "expense"})]}
        )
        # Create expense and link to request document
        expense_sheet = self._create_expense_sheet(
            [
                {
                    "product_id": self.product1,  # KPI1 = 2000.0
                    "product_qty": 2,
                    "price_unit": 1000.0,
                    "analytic_distribution": analytic_distribution,
                },
                {
                    "product_id": self.product2,  # KPI2 = 401.0
                    "product_qty": 1,
                    "price_unit": 401.0,
                    "analytic_distribution": analytic_distribution,
                },
            ]
        )
        expense_sheet._compute_from_employee_id()
        expense_sheet.request_document_id = request_order.line_ids.id

        self.assertEqual(len(request_order.line_ids), 1)
        self.assertEqual(len(request_order.line_ids.expense_sheet_ids), 1)

        request_order = request_order.with_context(
            force_date_commit=expense_sheet.expense_line_ids[0].date
        )

        # kpi 1 (kpi1) & CostCenter1, will result in $ -1.00
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            request_order.action_submit()
        request_order.action_draft()
        self.assertEqual(request_order.state, "draft")

        # Change price 401 to 300, it should not error
        expense_sheet.expense_line_ids.filtered(
            lambda exp: exp.product_id == self.product2
        ).with_context(allow_edit=1).write({"total_amount_currency": 300})
        request_order.action_submit()
        self.assertEqual(request_order.state, "submit")
        self.assertFalse(request_order.line_ids.line_data_amount)
        request_order.action_approve()
        self.assertEqual(request_order.state, "approve")
        self.assertEqual(expense_sheet.state, "draft")
        self.assertTrue(request_order.line_ids.line_data_amount)
        self.assertEqual(len(request_order.budget_move_ids), 2)
        self.assertAlmostEqual(self.budget_control.amount_balance, 100.0)  # 2400 - 2300
        self.assertAlmostEqual(self.budget_control.amount_request, 2300.0)
        self.assertAlmostEqual(self.budget_control.amount_expense, 0.0)

        # Request change state to done and expense sheet change to submit
        # default config is submit
        request_order.action_process_document()
        self.assertEqual(len(request_order.budget_move_ids), 2)
        self.assertAlmostEqual(self.budget_control.amount_balance, 100.0)  # 2400 - 2300
        self.assertAlmostEqual(self.budget_control.amount_request, 2300.0)
        self.assertAlmostEqual(self.budget_control.amount_expense, 0.0)
        self.assertEqual(expense_sheet.state, "submit")
        self.assertEqual(request_order.state, "done")

        # Approve expense, request document should close budget.
        expense_sheet.action_approve_expense_sheets()
        self.assertEqual(len(request_order.budget_move_ids), 4)
        self.assertEqual(expense_sheet.state, "approve")
        self.assertEqual(request_order.state, "done")
        self.assertEqual(self.budget_control.amount_balance, 100.0)
        self.assertEqual(self.budget_control.amount_request, 0.0)
        self.assertEqual(self.budget_control.amount_expense, 2300.0)

        # Reset expense, request document should receompute
        expense_sheet.action_reset_expense_sheets()
        self.assertEqual(len(request_order.budget_move_ids), 2)
        self.assertEqual(expense_sheet.state, "draft")
        self.assertEqual(request_order.state, "done")
        request_order.recompute_budget_move()
        self.assertEqual(self.budget_control.amount_balance, 100.0)
        self.assertEqual(self.budget_control.amount_request, 2300.0)
        self.assertEqual(self.budget_control.amount_expense, 0.0)

        # Test changed amount document, Request budget should uncommit same value
        expense_sheet.expense_line_ids.with_context(allow_edit=1).write(
            {"total_amount_currency": 500.0}
        )
        request_order.recompute_budget_move()
        self.assertAlmostEqual(self.budget_control.amount_balance, 100.0)  # 2400 - 2300
        self.assertAlmostEqual(
            self.budget_control.amount_request, 2300.0
        )  # request commit use 2300
        self.assertAlmostEqual(self.budget_control.amount_expense, 0.0)

        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        self.assertEqual(len(request_order.budget_move_ids), 4)
        self.assertAlmostEqual(
            self.budget_control.amount_balance, 1400.0
        )  # 2400 - 1000
        self.assertAlmostEqual(self.budget_control.amount_request, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_expense, 1000.0)
