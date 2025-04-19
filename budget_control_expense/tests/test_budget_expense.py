# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.budget_control.tests.common import get_budget_common_class


@tagged("post_install", "-at_install")
class TestBudgetControlExpense(get_budget_common_class()):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        # Create budget plan with 1 analytic
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
    def test_01_budget_expense(self):
        """
        On Expense Sheet
        (1) Test case, no budget check -> OK
        (2) Check Budget with analytic_kpi -> Error amount exceed on kpi1
        (3) Check Budget with analytic -> OK
        (2) Check Budget with analytic -> Error amount exceed
        """
        # Controlled budget
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)

        # Prepare Expense Sheet
        analytic_distribution = {str(self.costcenter1.id): 100}
        sheet = self._create_expense_sheet(
            [
                {
                    "product_id": self.product1,  # KPI1 = 401 -> error
                    "product_qty": 1,
                    "price_unit": 401,
                    "analytic_distribution": analytic_distribution,
                },
                {
                    "product_id": self.product2,  # KPI2 = 798
                    "product_qty": 2,
                    "price_unit": 399,
                    "analytic_distribution": analytic_distribution,
                },
            ]
        )
        # (1) No budget check first
        self.budget_period.control_budget = False
        self.budget_period.control_level = "analytic_kpi"
        # force date commit, as freeze_time not work for write_date
        sheet = sheet.with_context(force_date_commit=sheet.expense_line_ids[:1].date)
        sheet.action_submit_sheet()  # No budget check no error

        # (2) Check Budget with analytic_kpi -> Error
        sheet.action_reset_expense_sheets()
        self.budget_period.control_budget = True  # Set to check budget
        # kpi 1 (kpi1) & CostCenter1, will result in $ -1.00
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            sheet.action_submit_sheet()
        sheet.action_reset_expense_sheets()

        # (3) Check Budget with analytic -> OK
        self.budget_period.control_level = "analytic"
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()  # commit budget
        self.assertAlmostEqual(self.budget_control.amount_expense, 1199.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 1201.0)
        sheet.action_reset_expense_sheets()
        self.assertAlmostEqual(self.budget_control.amount_expense, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2400.0)

        # (4) Amount exceed -> Error
        sheet.expense_line_ids.write({"total_amount_currency": 1200.5})
        # CostCenter1, will result in $ -1.00
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            sheet.action_submit_sheet()

        # (5) Delete Expense Sheet
        sheet.action_reset_expense_sheets()
        sheet.expense_line_ids.write({"total_amount_currency": 100.0})
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        self.assertAlmostEqual(self.budget_control.amount_expense, 200.0)  # 2 lines
        self.assertAlmostEqual(self.budget_control.amount_balance, 2200.0)  # 2 lines
        sheet.unlink()
        self.assertAlmostEqual(self.budget_control.amount_expense, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2400.0)

    @freeze_time("2001-02-01")
    def test_02_budget_expense_to_journal_posting(self):
        """Expense to Journal Posting, commit and uncommit"""
        # Controlled budget
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)

        # Prepare Expense on kpi1 with qty 3 and unit_price 10
        analytic_distribution = {str(self.costcenter1.id): 100}
        sheet = self._create_expense_sheet(
            [
                {
                    "product_id": self.product1,  # KPI1
                    "product_qty": 3,
                    "price_unit": 10,
                    "analytic_distribution": analytic_distribution,
                },
            ]
        )
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        sheet = sheet.with_context(force_date_commit=sheet.expense_line_ids[:1].date)
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        # Expense = 30, JE Actual = 0, Balance = 2370
        self.assertAlmostEqual(self.budget_control.amount_expense, 30.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2370.0)
        # Create and post invoice
        sheet.action_sheet_move_post()
        move = sheet.account_move_ids
        self.assertAlmostEqual(move.state, "posted")
        # EX Commit = 0, JE Actual = 30, Balance = 2370
        self.assertAlmostEqual(self.budget_control.amount_expense, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 30.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2370.0)
        # Set to draft
        move.button_draft()
        # Update budget info
        self.assertAlmostEqual(self.budget_control.amount_expense, 30.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2370.0)
        # Cancel journal entry, expense no change
        move.button_cancel()
        self.assertAlmostEqual(self.budget_control.amount_expense, 30.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2370.0)

    @freeze_time("2001-02-01")
    def test_03_budget_recompute_and_close_budget_move(self):
        """EX to JE
        - Test recompute on both EX and JE
        - Test close on both EX and JE"""
        # Controlled budget
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)

        # Prepare Expense on kpi1 with qty 3 and unit_price 10
        analytic_distribution = {str(self.costcenter1.id): 100}
        sheet = self._create_expense_sheet(
            [
                {
                    "product_id": self.product1,
                    "product_qty": 2,
                    "price_unit": 15,
                    "analytic_distribution": analytic_distribution,
                },
                {
                    "product_id": self.product2,
                    "product_qty": 4,
                    "price_unit": 10,
                    "analytic_distribution": analytic_distribution,
                },
            ]
        )
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        sheet = sheet.with_context(force_date_commit=sheet.expense_line_ids[:1].date)
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        # Expense = 70, JE Actual = 0
        self.assertAlmostEqual(self.budget_control.amount_expense, 70.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)
        # Create and post invoice
        sheet.action_sheet_move_post()
        move = sheet.account_move_ids
        self.assertAlmostEqual(move.state, "posted")
        # EX Commit = 0, JE Actual = 70
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_expense, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 70.0)
        # Recompute
        sheet.recompute_budget_move()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_expense, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 70.0)
        move.recompute_budget_move()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_expense, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 70.0)
        # Close
        sheet.close_budget_move()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_expense, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 70.0)
        move.close_budget_move()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_expense, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)
