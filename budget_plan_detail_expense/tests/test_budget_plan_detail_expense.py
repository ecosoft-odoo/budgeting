# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.budget_plan_detail.tests.test_budget_plan_detail import (
    TestBudgetPlanDetail,
)


@tagged("post_install", "-at_install")
class TestBudgetPlanDetailExpense(TestBudgetPlanDetail):
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
                ex.total_amount_currency = (
                    ex_line["price_unit"] * ex_line["product_qty"]
                )
                ex.analytic_distribution = ex_line["analytic_distribution"]
            expense = ex.save()
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
    def test_01_budget_plan_check_over_limit_expense(self):
        """Create same analytic, difference fund, difference analytic tags
        line 1: Costcenter1, Fund1, Tag1, 600.0
        line 2: Costcenter1, Fund1, Tag2, 600.0
        line 3: Costcenter1, Fund2, Tag1, 600.0
        line 4: Costcenter1, Fund2,     , 600.0
        line 5: CostcenterX, Fund1, Tag1, 600.0
        line 6: CostcenterX, Fund2, Tag1, 600.0
        line 7: CostcenterX, Fund2, Tag2, 600.0
        line 8: CostcenterX, Fund1,     , 600.0
        """
        self._create_budget_plan_line_detail(self.budget_plan)
        self.budget_plan.action_confirm_plan_detail()
        self.budget_plan.action_confirm()
        self.assertEqual(self.budget_plan.state, "confirm")
        self.budget_plan.action_create_update_budget_control()
        self.budget_plan.action_done()

        self.assertEqual(self.budget_plan.state, "done")

        # Refresh data and Prepare budget control
        self.budget_plan.invalidate_recordset()
        # Get 1 budget control, Costcenter1 has 4 plan detail
        budget_control = self.budget_plan.budget_control_ids[0]
        budget_control.template_line_ids = [
            self.template_line1.id,
            self.template_line2.id,
            self.template_line3.id,
        ]

        # Test item created for 3 kpi x 4 quarters = 12 budget items
        budget_control.prepare_budget_control_matrix()
        assert len(budget_control.line_ids) == 12
        # Costcenter1 has 3 plan detail
        # Assign budget.control amount: KPI1 = 1500, 500, 400
        bc_items = budget_control.line_ids.filtered(lambda x: x.kpi_id == self.kpi1)
        bc_items[0].write({"amount": 1500})
        bc_items[1].write({"amount": 500})
        bc_items[2].write({"amount": 400})

        self.assertEqual(
            budget_control.mapped("plan_line_detail_ids"),
            self.budget_plan.line_detail_ids.filtered(
                lambda line: line.budget_control_id == budget_control
            ),
        )

        # Control budget
        budget_control.action_submit()
        budget_control.action_done()
        self.budget_period.control_budget = True

        # We allocate budget to Costcenter1 each 600.0 (total is 2400.0)
        analytic_distribution = {self.costcenter1.id: 100}

        # Commit expense without allocation (no fund, no tags)
        sheet = self._create_expense_sheet(
            [
                {
                    "product_id": self.product1,
                    "product_qty": 1,
                    "price_unit": 601.0,
                    "analytic_distribution": analytic_distribution,
                },
            ]
        )
        # force date commit, as freeze_time not work for write_date
        sheet = sheet.with_context(force_date_commit=sheet.expense_line_ids[:1].date)
        with self.assertRaisesRegex(
            UserError, "is not allocated on budget plan detail"
        ):
            sheet.action_submit_sheet()
        sheet.action_reset_expense_sheets()

        # Add fund1, tags1 in expense line
        sheet.expense_line_ids.fund_id = self.fund1_g1.id
        sheet.expense_line_ids.analytic_tag_ids = [(4, self.analytic_tag1.id)]

        # If line have tax_ids, it will commit with no tax
        # Tax Amount = 601 * 15% = 90.15
        # Total Amount without Tax = 601 - 90.15 = 510.85
        self.assertTrue(sheet.expense_line_ids.tax_ids)
        sheet.action_submit_sheet()
        sheet.action_reset_expense_sheets()

        # Expense commit amount 601 and no tax > allocated amount 600.0, it should error
        sheet.expense_line_ids.tax_ids = False
        with self.assertRaisesRegex(
            UserError, "spend amount over budget plan detail limit"
        ):
            sheet.action_submit_sheet()
        sheet.action_reset_expense_sheets()

        sheet.expense_line_ids.total_amount_currency = 400.0
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        move = sheet.account_move_ids
        self.assertAlmostEqual(move.state, "draft")
        self.assertEqual(sheet.budget_move_ids.fund_id, self.fund1_g1)
        self.assertEqual(sheet.budget_move_ids.analytic_tag_ids, self.analytic_tag1)
        self.assertEqual(move.invoice_line_ids.fund_id, self.fund1_g1)
        self.assertEqual(move.invoice_line_ids.analytic_tag_ids, self.analytic_tag1)
        self.assertAlmostEqual(budget_control.amount_expense, 400.0)
        self.assertAlmostEqual(budget_control.amount_actual, 0.0)
        self.assertAlmostEqual(budget_control.amount_balance, 2000.0)

        # Post journal entry
        sheet.action_sheet_move_post()
        self.assertAlmostEqual(move.state, "posted")

        self.assertAlmostEqual(budget_control.amount_expense, 0.0)
        self.assertAlmostEqual(budget_control.amount_actual, 400.0)
        self.assertAlmostEqual(budget_control.amount_balance, 2000.0)
