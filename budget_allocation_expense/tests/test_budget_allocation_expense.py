# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.budget_allocation.tests.test_budget_allocation import TestBudgetAllocation


@tagged("post_install", "-at_install")
class TestBudgetAllocationExpense(TestBudgetAllocation):
    @classmethod
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
                ex.fund_id = ex_line["fund_id"]
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
        budget_control.write({"template_line_ids": [self.template_line1.id]})
        # Test item created for 1 kpi x 4 quarters = 4 budget items
        budget_control.prepare_budget_control_matrix()
        assert len(budget_control.line_ids) == 4
        # Assign budget.control amount: 250
        with Form(budget_control.line_ids[0]) as line:
            line.amount = 250
        # Control budget
        budget_control.action_done()
        self.budget_period.control_budget = True
        # Commit actual without allocation (no fund, no tags)
        expense = self._create_expense_sheet(
            [
                {
                    "product_id": self.product1,
                    "product_qty": 1,
                    "price_unit": 30,
                    "analytic_id": self.costcenter1,
                    "fund_id": self.fund1_g1
                },
            ]
        )
        # force date commit, as freeze_time not work for write_date
        expense = expense.with_context(
            force_date_commit=expense.expense_line_ids[:1].date
        )
        with self.assertRaises(UserError):
            expense.action_submit_sheet()  # No allocated fund1, False (tags)
        # Add tags1 in expense line
        expense.expense_line_ids.analytic_tag_ids = [(4, self.analytic_tag1.id)]
        expense.action_submit_sheet()
        expense.approve_expense_sheets()
        self.assertEqual(expense.budget_move_ids.fund_id, self.fund1_g1)
        self.assertEqual(expense.budget_move_ids.analytic_tag_ids, self.analytic_tag1)
        expense.action_sheet_move_create()
        move = expense.account_move_id
        self.assertEqual(move.line_ids.mapped("fund_id"), self.fund1_g1)
        self.assertEqual(move.line_ids.mapped("analytic_tag_ids"), self.analytic_tag1)