# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.budget_activity.tests.test_budget_activity import TestBudgetActivity


@tagged("post_install", "-at_install")
class TestBudgetActivityAdvance(TestBudgetActivity):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        cls.kpi_advance = cls.env.ref(
            "budget_activity_advance_clearing.budget_kpi_advance"
        )
        cls.advance_product = cls.env.ref(
            "hr_expense_advance_clearing.product_emp_advance"
        )
        cls.advance_activity = cls.env.ref(
            "budget_activity_advance_clearing.budget_activity_advance"
        )
        # Add advance activity on template line
        cls.template_line_advance = cls.env["budget.template.line"].create(
            {
                "template_id": cls.template.id,
                "kpi_id": cls.kpi_advance.id,
                "account_ids": [(4, cls.account_kpiAV.id)],
            }
        )
        # Onchange activity on template line
        with Form(cls.template_line1) as line:
            line.kpi_id = cls.kpi_advance

    @freeze_time("2001-02-01")
    def _create_advance_sheet(self, amount, analytic):
        Expense = self.env["hr.expense"]
        view_id = "hr_expense_advance_clearing.hr_expense_view_form"
        user = self.env.ref("base.user_admin")
        with Form(Expense.with_context(default_advance=True), view=view_id) as ex:
            ex.employee_id = user.employee_id
            ex.unit_amount = amount
            ex.analytic_account_id = analytic
        advance = ex.save()
        expense_sheet = self.env["hr.expense.sheet"].create(
            {
                "name": "Test Advance",
                "employee_id": user.employee_id.id,
                "expense_line_ids": [(6, 0, [advance.id])],
            }
        )
        return expense_sheet

    @freeze_time("2001-02-01")
    def _create_clearing_sheet(self, advance, ex_lines):
        Expense = self.env["hr.expense"]
        view_id = "hr_expense_advance_clearing.hr_expense_view_form"
        expense_ids = []
        user = self.env.ref("base.user_admin")
        for ex_line in ex_lines:
            with Form(Expense, view=view_id) as ex:
                ex.employee_id = user.employee_id
                ex.product_id = ex_line["product_id"]
                ex.quantity = ex_line["product_qty"]
                ex.unit_amount = ex_line["price_unit"]
                ex.analytic_account_id = ex_line["analytic_id"]
            expense = ex.save()
            expense_ids.append(expense.id)
        expense_sheet = self.env["hr.expense.sheet"].create(
            {
                "name": "Test Expense",
                "advance_sheet_id": advance and advance.id,
                "employee_id": user.employee_id.id,
                "expense_line_ids": [(6, 0, expense_ids)],
            }
        )
        return expense_sheet

    @freeze_time("2001-02-01")
    def test_01_budget_activity_advance(self):
        """
        On expense,
        - If no activity, budget follows product's account
        - If activity is selected, account follows activity's regardless of product
        - User can always change account code afterwards
        - Posting invoice, will create budget move with activity
        """
        # Control budget
        self.budget_period.control_budget = True
        self.budget_control.action_done()
        # Can not create advance if not set account_id
        with self.assertRaises(UserError):
            self._create_advance_sheet(100, self.costcenter1)
        # Configure the account in the activity advance.
        # This should also update the account in the product advance.
        self.assertFalse(self.advance_product.property_account_expense_id)
        self.assertFalse(self.advance_activity.account_id)
        with Form(self.advance_activity) as activity:
            activity.account_id = self.account_kpiAV
        activity.save()
        self.assertEqual(
            self.advance_product.property_account_expense_id, self.account_kpiAV
        )
        self.assertEqual(self.advance_activity.account_id, self.account_kpiAV)

        advance = self._create_advance_sheet(100, self.costcenter1)
        # Check change activity is not equal activity_advance
        with self.assertRaises(UserError):
            advance.expense_line_ids.activity_id = self.activity2.id
            advance.expense_line_ids._check_advance()
        # force date commit, as freeze_time not work for write_date
        advance = advance.with_context(
            force_date_commit=advance.expense_line_ids[:1].date
        )
        advance.action_submit_sheet()
        advance.action_submit_sheet()
        advance.approve_expense_sheets()
        # Post journal entry
        advance.action_sheet_move_create()
        # Make payment full amount = 100
        advance.action_register_payment()
        f = Form(
            self.env["account.payment.register"].with_context(
                active_model="account.move",
                active_ids=[advance.account_move_id.id],
            )
        )
        wizard = f.save()
        wizard.action_create_payments()
        self.assertEqual(advance.clearing_residual, 100.0)
        self.assertEqual(self.budget_control.amount_advance, 100.0)
        self.assertEqual(self.budget_control.amount_balance, 2300.0)
        # Test clearing activity with advance activity, it should error when submit
        advance.expense_line_ids.clearing_activity_id = self.advance_activity
        # ------------------ Clearing --------------------------
        user = self.env.ref("base.user_admin")
        with Form(self.env["hr.expense.sheet"]) as sheet:
            sheet.name = "Test Clearing"
            sheet.employee_id = user.employee_id
        ex_sheet = sheet.save()
        ex_sheet.advance_sheet_id = advance
        self.assertEqual(len(ex_sheet.expense_line_ids), 0)
        ex_sheet._onchange_advance_sheet_id()
        self.assertEqual(len(ex_sheet.expense_line_ids), 1)
        with self.assertRaises(
            UserError
        ):  # clearing activity must not equal advance activity
            ex_sheet.action_submit_sheet()
        # Change activity is not equal advance activity
        ex_sheet.expense_line_ids.activity_id = self.activity3
        ex_sheet.expense_line_ids.total_amount = 100.0
        ex_sheet.action_submit_sheet()
        ex_sheet.approve_expense_sheets()
