# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.budget_allocation.tests.test_budget_allocation import (
    TestBudgetAllocation,
)


@tagged("post_install", "-at_install")
class TestBudgetAllocationAdvance(TestBudgetAllocation):
    @classmethod
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
        cls.advance_product = cls.env.ref(
            "hr_expense_advance_clearing.product_emp_advance"
        ).write({"property_account_expense_id": cls.account_kpiAV.id})

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
    def test_01_commitment_expense_fund(self):
        """Create same analytic, difference fund, difference analytic tags
        line 1: Costcenter1, Fund1, Tag1, 50.0
        line 2: Costcenter1, Fund1, Tag2, 100.0
        line 3: Costcenter1, Fund2,     , 100.0
        line 4: CostcenterX, Fund1,     , 100.0
        """
        # budget control is depends on budget allocation
        budget_control_ids = self.test_02_process_budget_allocation()
        # Test with 1 budget control, it can commit budget not over 250
        budget_control = budget_control_ids[0]
        self.assertEqual(
            sum(budget_control.allocation_line_ids.mapped("allocated_amount")), 250
        )
        budget_control.write({"template_line_ids": [self.template_lineAV.id]})
        # Test item created for 1 kpi x 4 quarters = 4 budget items
        budget_control.prepare_budget_control_matrix()
        assert len(budget_control.line_ids) == 4
        # Assign budget.control amount: 250
        with Form(budget_control.line_ids[0]) as line:
            line.amount = 250
        # Control budget
        budget_control.action_done()
        self.budget_period.control_budget = True
        # Commit advance without allocation (no fund, no tags)
        advance = self._create_advance_sheet(30, self.costcenter1)
        # force date commit, as freeze_time not work for write_date
        advance = advance.with_context(
            force_date_commit=advance.expense_line_ids[:1].date
        )
        with self.assertRaises(UserError):
            advance.action_submit_sheet()

        # Add fund1, tags1 in expense line
        advance.expense_line_ids.fund_id = self.fund1_g1
        advance.expense_line_ids.analytic_tag_ids = [(4, self.analytic_tag1.id)]
        advance.action_submit_sheet()
        advance.approve_expense_sheets()
        self.assertEqual(advance.advance_budget_move_ids.fund_id, self.fund1_g1)
        self.assertEqual(
            advance.advance_budget_move_ids.analytic_tag_ids, self.analytic_tag1
        )
        self.assertFalse(advance.budget_move_ids)
