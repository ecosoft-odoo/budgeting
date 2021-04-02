# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from freezegun import freeze_time

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.budget_control.tests.common import BudgetControlCommon


@tagged("post_install", "-at_install")
class TestBudgetControl(BudgetControlCommon):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        # Additional KPI for advance
        cls.kpiAV = cls.env["mis.report.kpi"].create(
            dict(
                report_id=cls.report.id,
                name="kpiAV",
                budgetable=True,
                description="kpi AV",
                expression="balp[KPIAV]",
            )
        )
        # Create sample ready to use Budget Control
        cls.budget_control = cls.BudgetControl.create(
            {
                "name": "CostCenter1/%s" % cls.year,
                "budget_id": cls.budget_period.mis_budget_id.id,
                "analytic_account_id": cls.costcenter1.id,
                "plan_date_range_type_id": cls.date_range_type.id,
            }
        )
        # Test item created for 4 kpi x 4 quarters = 16 budget items
        assert len(cls.budget_control.item_ids) == 16
        # Assign budget.control amount: KPI1 = 100, KPI2=800, Total=300
        cls.budget_control.item_ids.filtered(
            lambda x: x.kpi_expression_id == cls.kpi1.expression_ids[0]
        )[:1].write({"amount": 100})
        cls.budget_control.item_ids.filtered(
            lambda x: x.kpi_expression_id == cls.kpi2.expression_ids[0]
        )[:1].write({"amount": 200})
        cls.budget_control.allocated_amount = 300
        cls.budget_control.action_done()
        # Set advance account
        product = cls.env.ref(
            "hr_expense_advance_clearing.product_emp_advance"
        )
        product.property_account_expense_id = cls.account_kpiAV

    @freeze_time("2001-02-01")
    def _create_advance_sheet(self, amount, analytic):
        Expense = self.env["hr.expense"]
        view_id = "hr_expense_advance_clearing.hr_expense_view_form"
        ctx = {}
        user = self.env.ref("base.user_admin")
        with Form(Expense.with_context(ctx), view=view_id) as ex:
            ex.employee_id = user.employee_id
            ex.advance = True
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
        ctx = {}
        expense_ids = []
        user = self.env.ref("base.user_admin")
        for ex_line in ex_lines:
            with Form(Expense.with_context(ctx), view=view_id) as ex:
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
    def test_01_budget_advance(self):
        """
        Create Advance,
        - Budget will be committed into advance.budget.move
        - No actual on JE
        """
        # KPI1 = 100, KPI2 = 200, Total = 300
        self.assertEqual(300, self.budget_control.amount_budget)
        # Create advance = 100
        advance = self._create_advance_sheet(100, self.costcenter1)
        # (1) No budget check first
        self.budget_period.advance = False
        self.budget_period.control_level = "analytic_kpi"
        # force date commit, as freeze_time not work for write_date
        advance = advance.with_context(
            force_date_commit=advance.expense_line_ids[:1].date
        )
        advance.action_submit_sheet()  # No budget check no error
        # (2) Check Budget with analytic_kpi -> Error
        advance.reset_expense_sheets()
        self.budget_period.advance = True  # Set to check budget
        # kpi 1 (kpi1) & CostCenter1, will result in $ -1.00
        with self.assertRaises(UserError):
            advance.action_submit_sheet()
        # (3) Check Budget with analytic -> OK
        advance.reset_expense_sheets()
        self.budget_period.control_level = "analytic"
        advance.action_submit_sheet()
        advance.approve_expense_sheets()
        self.assertEqual(self.budget_control.amount_advance, 100)
        self.assertEqual(self.budget_control.amount_balance, 200)
        # Post journal entry
        advance.action_sheet_move_create()
        move = advance.account_move_id
        self.assertEqual(move.state, "posted")
        self.assertTrue(move.not_affect_budget)
        self.assertFalse(move.budget_move_ids)
        self.assertEqual(self.budget_control.amount_advance, 100)
        self.assertEqual(self.budget_control.amount_actual, 0)
        self.assertEqual(self.budget_control.amount_balance, 200)
        # Reset
        advance.reset_expense_sheets()
        self.assertEqual(self.budget_control.amount_advance, 0)
        self.assertEqual(self.budget_control.amount_balance, 300)
        # (4) Amount exceed -> Error
        advance.expense_line_ids.write({"unit_amount": 301})
        # CostCenter1, will result in $ -1.00
        with self.assertRaises(UserError):
            advance.action_submit_sheet()

    @freeze_time("2001-02-01")
    def test_02_budget_advance_clearing(self):
        """Advance 100 (which is equal to budget amount), with clearing cases when,
        - Clearing 80, the uncommit advance should be 80
        - Clearing 120, the uncommit advance should be 100 (max)
        """
        # KPI1 = 100, KPI2 = 200, Total = 300
        self.assertEqual(300, self.budget_control.amount_budget)
        # Create advance = 100
        advance = self._create_advance_sheet(100, self.costcenter1)
        self.budget_period.advance = True
        self.budget_period.expense = True
        self.budget_period.control_level = "analytic"
        advance = advance.with_context(
            force_date_commit=advance.expense_line_ids[:1].date
        )
        advance.action_submit_sheet()
        advance.approve_expense_sheets()
        advance.action_sheet_move_create()
        # Advance 100, Clearing = 0, Balance = 200
        self.assertEqual(self.budget_control.amount_advance, 100)
        self.assertEqual(self.budget_control.amount_expense, 0)
        self.assertEqual(self.budget_control.amount_balance, 200)
        # Create Clearing = 80 to this advance
        clearing = self._create_clearing_sheet(
            advance,
            [
                {
                    "product_id": self.product1,  # KPI1 = 120
                    "product_qty": 1,
                    "price_unit": 20,
                    "analytic_id": self.costcenter1,
                },
                {
                    "product_id": self.product2,  # KPI2 = 80
                    "product_qty": 2,
                    "price_unit": 30,
                    "analytic_id": self.costcenter1,
                },
            ],
        )
        clearing = clearing.with_context(
            force_date_commit=clearing.expense_line_ids[:1].date
        )
        clearing.action_submit_sheet()
        clearing.approve_expense_sheets()
        # Advance 20, Clearing = 80, Balance = 200
        self.assertEqual(self.budget_control.amount_advance, 20)
        self.assertEqual(self.budget_control.amount_expense, 80)
        self.assertEqual(self.budget_control.amount_balance, 200)
        # Refuse
        clearing.refuse_sheet("Refuse it!")
        self.assertEqual(self.budget_control.amount_advance, 100)
        self.assertEqual(self.budget_control.amount_expense, 0)
        self.assertEqual(self.budget_control.amount_balance, 200)
        # Change line 1 amount to exceed
        clearing.expense_line_ids[:1].unit_amount = 100
        with self.assertRaises(ValidationError):
            clearing.action_submit_sheet()
