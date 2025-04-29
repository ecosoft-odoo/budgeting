# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo.tests import Form, tagged

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
    def _create_advance_sheet(self, amount, analytic_distribution):
        Expense = self.env["hr.expense"]
        view_id = "hr_expense_advance_clearing.hr_expense_view_form"
        user = self.env.ref("base.user_admin")
        with Form(
            Expense.with_context(
                default_advance=True, default_activity_id=self.advance_activity
            ),
            view=view_id,
        ) as ex:
            ex.employee_id = user.employee_id
            ex.total_amount_currency = amount
            ex.analytic_distribution = analytic_distribution
        advance = ex.save()
        expense_sheet = self.env["hr.expense.sheet"].create(
            {
                "name": "Test Advance",
                "advance": True,
                "employee_id": user.employee_id.id,
                "expense_line_ids": [(6, 0, [advance.id])],
            }
        )
        return expense_sheet

    @freeze_time("2001-02-01")
    def test_01_budget_activity_advance_control_analytic(self):
        """
        On expense (advnace/clearing),
        - If no activity, budget follows product's account
        - If activity is selected, account follows activity's regardless of product
        """
        self.budget_period.control_level = "analytic"
        self.assertEqual(self.budget_period.control_level, "analytic")

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

        analytic_distribution = {str(self.costcenter1.id): 100}
        advance_sheet = self._create_advance_sheet(1201, analytic_distribution)

        # force date commit, as freeze_time not work for write_date
        advance_sheet = advance_sheet.with_context(
            force_date_commit=advance_sheet.expense_line_ids[:1].date
        )

        # Can commit budget because control level analytic (2400.0)
        advance_sheet.action_submit_sheet()
        advance_sheet.action_approve_expense_sheets()

        # Check move must have activity in line
        move = advance_sheet.account_move_ids
        # AV Commit = 1201.0, EX Commit = 0.0, INV Actual = 0.0, Balance = 1199.0
        self.assertAlmostEqual(self.budget_control.amount_advance, 1201.0)
        self.assertAlmostEqual(self.budget_control.amount_expense, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 1199.0)
        self.assertEqual(
            advance_sheet.advance_budget_move_ids.account_id,
            advance_sheet.expense_line_ids.activity_id.account_id,
        )
        self.assertEqual(
            advance_sheet.advance_budget_move_ids.activity_id,
            advance_sheet.expense_line_ids.activity_id,
        )
        self.assertEqual(move.invoice_line_ids.activity_id, self.advance_activity)
        self.assertEqual(
            move.invoice_line_ids.account_id, self.advance_activity.account_id
        )

        # post invoice
        advance_sheet.action_sheet_move_post()

        # AV Commit = 1201.0, EX Commit = 0.0, INV Actual = 0.0, Balance = 1199.0
        self.assertAlmostEqual(self.budget_control.amount_advance, 1201.0)
        self.assertAlmostEqual(self.budget_control.amount_expense, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 1199.0)
        # Advance create invoice not affect budget
        self.assertTrue(move.not_affect_budget)

        # Make payment full amount = 1201
        advance_sheet.action_register_payment()
        f = Form(
            self.env["account.payment.register"].with_context(
                active_model="account.move",
                active_ids=[move.id],
            )
        )
        wizard = f.save()
        wizard.action_create_payments()
        self.assertAlmostEqual(advance_sheet.clearing_residual, 1201.0)
        self.assertAlmostEqual(self.budget_control.amount_advance, 1201.0)
        self.assertAlmostEqual(self.budget_control.amount_expense, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 1199.0)

        # Test clearing activity with advance activity, it should error when submit
        advance_sheet.expense_line_ids.clearing_activity_id = self.advance_activity
        # ------------------ Clearing --------------------------
        user = self.env.ref("base.user_admin")
        with Form(self.env["hr.expense.sheet"]) as sheet:
            sheet.name = "Test Clearing"
            sheet.employee_id = user.employee_id
        ex_sheet = sheet.save()
        self.assertEqual(len(ex_sheet.expense_line_ids), 0)
        ex_sheet.advance_sheet_id = advance_sheet
        ex_sheet._onchange_advance_sheet_id()
        self.assertEqual(len(ex_sheet.expense_line_ids), 1)

        # Activity of clearing should default from clearing_activity_id
        self.assertEqual(ex_sheet.expense_line_ids.activity_id, self.advance_activity)
