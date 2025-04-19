# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.budget_control.tests.common import get_budget_common_class


@tagged("post_install", "-at_install")
class TestBudgetControlAdvance(get_budget_common_class()):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        # Additional KPI for advance
        cls.kpiAV = cls.BudgetKPI.create({"name": "kpi AV"})
        cls.template_lineAV = cls.env["budget.template.line"].create(
            {
                "template_id": cls.template.id,
                "kpi_id": cls.kpiAV.id,
                "account_ids": [(4, cls.account_kpiAV.id)],
            }
        )

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
            cls.template_lineAV.id,
        ]

        # Test item created for 4 kpi x 4 quarters = 16 budget items
        cls.budget_control.prepare_budget_control_matrix()
        assert len(cls.budget_control.line_ids) == 16
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

        # Set advance account
        product = cls.env.ref("hr_expense_advance_clearing.product_emp_advance")
        product.property_account_expense_id = cls.account_kpiAV

    @freeze_time("2001-02-01")
    def _create_advance_sheet(self, amount, analytic_distribution):
        Expense = self.env["hr.expense"]
        view_id = "hr_expense_advance_clearing.hr_expense_view_form"
        user = self.env.ref("base.user_admin")
        with Form(Expense.with_context(default_advance=True), view=view_id) as ex:
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
    def _create_clearing_sheet(self, advance, ex_lines):
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
            expense.tax_ids = False  # Test no vat
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
    def test_01_budget_advance(self):
        """
        Create Advance,
        - Budget will be committed into advance.budget.move
        - No actual on JE
        """
        # Controlled budget
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)

        analytic_distribution = {str(self.costcenter1.id): 100}
        # Create advance = 100
        advance = self._create_advance_sheet(100, analytic_distribution)
        # (1) No budget check first
        self.budget_period.advance = False
        self.budget_period.control_level = "analytic_kpi"
        # force date commit, as freeze_time not work for write_date
        advance = advance.with_context(
            force_date_commit=advance.expense_line_ids[:1].date
        )
        advance.action_submit_sheet()  # No budget check no error

        # (2) Check Budget with analytic_kpi -> Error
        advance.action_reset_expense_sheets()
        self.budget_period.control_budget = True  # Set to check budget
        # kpi 1 (kpi1) & CostCenter1, will result in $ -1.00
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            advance.action_submit_sheet()

        # (3) Check Budget with analytic -> OK
        self.budget_period.control_level = "analytic"
        advance.action_submit_sheet()
        advance.action_approve_expense_sheets()
        self.assertAlmostEqual(self.budget_control.amount_advance, 100.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2300.0)
        # Post journal entry
        advance.action_sheet_move_post()
        move = advance.account_move_ids
        self.assertEqual(move.state, "posted")
        self.assertTrue(move.not_affect_budget)
        self.assertFalse(move.budget_move_ids)
        self.assertAlmostEqual(self.budget_control.amount_advance, 100.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2300.0)
        # Reset
        advance.action_reset_expense_sheets()
        self.assertAlmostEqual(self.budget_control.amount_advance, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2400.0)

        # (4) Amount exceed -> Error
        advance.expense_line_ids.write({"total_amount": 2401})
        # CostCenter1, will result in $ -1.00
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            advance.action_submit_sheet()

    @freeze_time("2001-02-01")
    def test_02_budget_advance_clearing(self):
        """Advance 100 (which is equal to budget amount), with clearing cases when,
        - Clearing 80, the uncommit advance should be 20
        - Clearing 120, the uncommit advance should be 100 (max)
        """
        # Controlled budget
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)

        analytic_distribution = {str(self.costcenter1.id): 100}
        # Create advance = 100
        advance = self._create_advance_sheet(100, analytic_distribution)
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        advance = advance.with_context(
            force_date_commit=advance.expense_line_ids[:1].date
        )
        advance.action_submit_sheet()
        advance.action_approve_expense_sheets()
        advance.action_sheet_move_post()
        # Advance 100, Clearing = 0, Balance = 2300
        self.assertAlmostEqual(self.budget_control.amount_advance, 100.0)
        self.assertAlmostEqual(self.budget_control.amount_expense, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2300.0)
        # Create Total Clearing = 80 to this advance
        clearing = self._create_clearing_sheet(
            advance,
            [
                {
                    "product_id": self.product1,  # KPI1 = 20
                    "product_qty": 1,
                    "price_unit": 20,
                    "analytic_distribution": analytic_distribution,
                },
                {
                    "product_id": self.product2,  # KPI2 = 60
                    "product_qty": 2,
                    "price_unit": 30,
                    "analytic_distribution": analytic_distribution,
                },
            ],
        )
        clearing = clearing.with_context(
            force_date_commit=clearing.expense_line_ids[:1].date
        )
        clearing.action_submit_sheet()
        clearing.action_approve_expense_sheets()
        # Advance 20, Clearing = 80, Balance = 2300
        self.assertAlmostEqual(self.budget_control.amount_advance, 20.0)
        self.assertAlmostEqual(self.budget_control.amount_expense, 80.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2300.0)
        # Refuse
        clearing._do_refuse("Refuse it!")
        self.assertAlmostEqual(self.budget_control.amount_advance, 100.0)
        self.assertAlmostEqual(self.budget_control.amount_expense, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2300.0)
        # Change line 1 amount from 60 to 2381 (exceed), total is 2381 + 20
        clearing.expense_line_ids[:1].total_amount_currency = 2381
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            clearing.action_submit_sheet()
        clearing.action_reset_expense_sheets()

        # (5) Delete Clearing, Advance should be uncommitted
        clearing.expense_line_ids[:1].total_amount_currency = 50
        clearing.action_submit_sheet()
        clearing.action_approve_expense_sheets()
        # advance 100 - (50 + 20)
        self.assertAlmostEqual(self.budget_control.amount_advance, 30.0)
        # clearing 50 + 20
        self.assertAlmostEqual(self.budget_control.amount_expense, 70.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2300.0)
        # (5) Create move from expense
        clearing.action_sheet_move_post()
        self.assertAlmostEqual(self.budget_control.amount_advance, 30.0)
        self.assertAlmostEqual(self.budget_control.amount_expense, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 70.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2300.0)
        clearing.account_move_ids.button_draft()
        self.assertAlmostEqual(self.budget_control.amount_advance, 30.0)
        self.assertAlmostEqual(self.budget_control.amount_expense, 70.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2300.0)
        # (6) Delete Clearing, Advance should be uncommitted
        clearing.unlink()
        self.assertAlmostEqual(self.budget_control.amount_advance, 100)
        self.assertAlmostEqual(self.budget_control.amount_expense, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2300.0)

    @freeze_time("2001-02-01")
    def test_03_budget_recompute_and_close_budget_move(self):
        """
        After Advance 20, Clearing 80
        - Recompute both should be the same
        - Close budget both should be all zero
        """
        # Controlled budget
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)

        analytic_distribution = {str(self.costcenter1.id): 100}
        # Create advance = 100
        advance = self._create_advance_sheet(100, analytic_distribution)
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        advance = advance.with_context(
            force_date_commit=advance.expense_line_ids[:1].date
        )
        advance.action_submit_sheet()
        advance.action_approve_expense_sheets()
        advance.action_sheet_move_post()
        # Create Clearing = 80 to this advance
        clearing = self._create_clearing_sheet(
            advance,
            [
                {
                    "product_id": self.product1,  # KPI1 = 20
                    "product_qty": 1,
                    "price_unit": 20,
                    "analytic_distribution": analytic_distribution,
                },
                {
                    "product_id": self.product2,  # KPI2 = 60
                    "product_qty": 2,
                    "price_unit": 30,
                    "analytic_distribution": analytic_distribution,
                },
            ],
        )
        clearing = clearing.with_context(
            force_date_commit=clearing.expense_line_ids[:1].date
        )
        clearing.action_submit_sheet()
        clearing.action_approve_expense_sheets()
        # Advance 20, Clearing = 80, Balance = 2300
        self.assertAlmostEqual(self.budget_control.amount_advance, 20.0)
        self.assertAlmostEqual(self.budget_control.amount_expense, 80.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2300.0)
        # Recompute
        advance.recompute_budget_move()
        self.budget_control.invalidate_model()
        self.assertAlmostEqual(self.budget_control.amount_advance, 20.0)
        self.assertAlmostEqual(self.budget_control.amount_expense, 80.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2300.0)
        clearing.recompute_budget_move()
        self.budget_control.invalidate_model()
        self.assertAlmostEqual(self.budget_control.amount_advance, 20.0)
        self.assertAlmostEqual(self.budget_control.amount_expense, 80.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2300.0)
        # Close
        advance.close_budget_move()
        self.budget_control.invalidate_model()
        self.assertAlmostEqual(self.budget_control.amount_advance, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_expense, 80.0)
        clearing.close_budget_move()
        self.budget_control.invalidate_model()
        self.assertAlmostEqual(self.budget_control.amount_advance, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_expense, 0.0)

    @freeze_time("2001-02-01")
    def test_04_return_advance(self):
        """
        Create Advance 100, balance is 200
        - Return Advance 30
        - Balance should be 230
        """
        # Controlled budget
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)

        analytic_distribution = {str(self.costcenter1.id): 100}
        # Create advance = 100
        advance = self._create_advance_sheet(100, analytic_distribution)
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        advance = advance.with_context(
            force_date_commit=advance.expense_line_ids[:1].date
        )
        advance.action_submit_sheet()
        advance.action_approve_expense_sheets()
        advance.action_sheet_move_post()
        # Make payment full amount = 100
        advance.action_register_payment()
        f = Form(
            self.env["account.payment.register"].with_context(
                active_model="account.move",
                active_ids=[advance.account_move_ids.id],
            )
        )
        wizard = f.save()
        wizard.action_create_payments()
        self.assertAlmostEqual(advance.clearing_residual, 100.0)
        self.assertAlmostEqual(self.budget_control.amount_advance, 100.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2300.0)
        # Return advance = 30
        advance.with_context(
            hr_return_advance=True,
        ).action_register_payment()
        with Form(
            self.env["account.payment.register"].with_context(
                active_model="account.move",
                active_ids=[advance.account_move_ids.id],
                hr_return_advance=True,
            )
        ) as f:
            f.payment_date = fields.Date.today()
            f.amount = 30
        wizard = f.save()
        wizard.with_context(
            hr_return_advance=True,
        ).action_create_payments()
        self.assertAlmostEqual(advance.clearing_residual, 70.0)
        self.assertAlmostEqual(self.budget_control.amount_advance, 70.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2330.0)
