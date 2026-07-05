# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo import Command
from odoo.tests import Form, tagged

from odoo.addons.budget_control.tests.common import get_budget_common_class


@tagged("post_install", "-at_install")
class TestBudgetControlPettyCash(get_budget_common_class()):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        # Budget plan with 1 analytic / KPI1 = 2400
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
        cls.budget_plan.invalidate_recordset()

        cls.budget_control = cls.budget_plan.budget_control_ids
        cls.budget_control.template_line_ids = [
            cls.template_line1.id,
            cls.template_line2.id,
            cls.template_line3.id,
        ]
        cls.budget_control.prepare_budget_control_matrix()
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi1).write(
            {"amount": 100}
        )

        # Petty cash setup
        cls.petty_cash_account = cls.Account.create(
            {
                "name": "Petty Cash - Test",
                "code": "PCASH",
                "account_type": "asset_current",
                "reconcile": True,
            }
        )
        cls.petty_cash_journal = cls.env["account.journal"].create(
            {"name": "Petty Cash", "code": "PCJ", "type": "purchase"}
        )
        cls.petty_cash = cls.env["petty.cash"].create(
            {
                "partner_id": cls.vendor.id,
                "account_id": cls.petty_cash_account.id,
                "petty_cash_limit": 2000.0,
                "journal_id": cls.petty_cash_journal.id,
            }
        )
        # Refill the petty cash holder so the clearing entry can post.
        refill = cls.env["account.move"].create(
            {
                "partner_id": cls.vendor.id,
                "move_type": "in_invoice",
                "invoice_date": "2001-01-15",
                "is_petty_cash": True,
            }
        )
        refill._onchange_is_petty_cash()
        refill.invoice_line_ids.price_unit = 2000.0
        refill.action_post()
        cls.petty_cash._compute_petty_cash_balance()
        assert cls.petty_cash.petty_cash_balance == 2000.0

    @freeze_time("2001-02-01")
    def _create_petty_cash_expense_sheet(self, amount):
        Expense = self.env["hr.expense"]
        view_id = "hr_expense.hr_expense_view_form"
        user = self.env.ref("base.user_admin")
        analytic_distribution = {str(self.costcenter1.id): 100}
        with Form(Expense, view=view_id) as ex:
            ex.employee_id = user.employee_id
            ex.product_id = self.product1
            ex.total_amount_currency = amount
            ex.analytic_distribution = analytic_distribution
        expense = ex.save()
        expense.tax_ids = False
        expense.payment_mode = "petty_cash"
        expense.petty_cash_id = self.petty_cash
        sheet = self.env["hr.expense.sheet"].create(
            {
                "name": "Test Petty Cash Expense",
                "employee_id": user.employee_id.id,
                "expense_line_ids": [Command.set([expense.id])],
            }
        )
        return sheet

    @freeze_time("2001-02-01")
    def test_01_petty_cash_clearing_line_not_affect_budget(self):
        """The petty cash clearing (destination) line must not affect budget."""
        # Controlled budget
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"

        sheet = self._create_petty_cash_expense_sheet(amount=100.0)
        sheet = sheet.with_context(force_date_commit=sheet.expense_line_ids[:1].date)
        # Submit + approve => petty cash clearing entry is posted.
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()

        move = sheet.account_move_ids
        self.assertTrue(move, "Petty cash clearing entry should be posted.")
        self.assertEqual(move.move_type, "entry")

        # The destination line (petty cash account) must skip the budget.
        petty_cash_lines = move.line_ids.filtered(
            lambda line: line.account_id == self.petty_cash_account
        )
        self.assertTrue(petty_cash_lines, "Petty cash clearing line not found.")
        self.assertTrue(
            petty_cash_lines.mapped("not_affect_budget"),
            "Petty cash clearing line must be marked not_affect_budget.",
        )
        # The expense (source) line must still affect the budget.
        expense_lines = move.line_ids - petty_cash_lines
        expense_lines = expense_lines.filtered(lambda line: not line.tax_line_id)
        self.assertTrue(
            expense_lines,
            "Expense source line not found.",
        )
        self.assertFalse(
            expense_lines.mapped("not_affect_budget"),
            "Expense source line must affect the budget.",
        )
