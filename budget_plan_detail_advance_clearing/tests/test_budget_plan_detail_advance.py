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
class TestBudgetPlanDetailAdvance(TestBudgetPlanDetail):
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
                "expense_line_ids": [Command.set([advance.id])],
            }
        )
        return expense_sheet

    def test_01_budget_plan_check_over_limit_advance(self):
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
            self.template_lineAV.id,
        ]

        # Test item created for 4 kpi x 4 quarters = 16 budget items
        budget_control.prepare_budget_control_matrix()
        assert len(budget_control.line_ids) == 16
        # Costcenter1 has 3 plan detail
        # Assign budget.control amount: KPI1 = 1500, 500, 400
        bc_items = budget_control.line_ids.filtered(lambda x: x.kpi_id == self.kpiAV)
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
        self.budget_period.control_level = "analytic"

        # Commit advance without allocation (no fund, no tags)
        analytic_distribution = {str(self.costcenter1.id): 100}
        advance_sheet = self._create_advance_sheet(601, analytic_distribution)

        # force date commit, as freeze_time not work for write_date
        advance_sheet = advance_sheet.with_context(
            force_date_commit=advance_sheet.expense_line_ids[:1].date
        )

        with self.assertRaisesRegex(
            UserError, "is not allocated on budget plan detail"
        ):
            advance_sheet.action_submit_sheet()
        advance_sheet.action_reset_expense_sheets()

        # Add fund1, tags1 in expense line
        advance_sheet.expense_line_ids.fund_id = self.fund1_g1
        advance_sheet.expense_line_ids.analytic_tag_ids = [(4, self.analytic_tag1.id)]

        # Add product for clearing
        advance_sheet.expense_line_ids.clearing_product_id = self.env.ref(
            "product.product_product_3"
        )

        # Advance commit amount 601 and no tax > allocated amount 600.0, it should error
        with self.assertRaisesRegex(
            UserError, "spend amount over budget plan detail limit"
        ):
            advance_sheet.action_submit_sheet()
        advance_sheet.action_reset_expense_sheets()

        advance_sheet.expense_line_ids.total_amount = 400.0
        advance_sheet.action_submit_sheet()
        advance_sheet.action_approve_expense_sheets()
        move = advance_sheet.account_move_ids
        self.assertAlmostEqual(move.state, "draft")
        self.assertEqual(advance_sheet.advance_budget_move_ids.fund_id, self.fund1_g1)
        self.assertEqual(
            advance_sheet.advance_budget_move_ids.analytic_tag_ids, self.analytic_tag1
        )
        self.assertEqual(move.invoice_line_ids.fund_id, self.fund1_g1)
        self.assertEqual(move.invoice_line_ids.analytic_tag_ids, self.analytic_tag1)
        self.assertAlmostEqual(budget_control.amount_advance, 400.0)
        self.assertAlmostEqual(budget_control.amount_expense, 0.0)
        self.assertAlmostEqual(budget_control.amount_balance, 2000.0)

        # Post journal entry
        advance_sheet.action_sheet_move_post()
        self.assertAlmostEqual(move.state, "posted")

        self.assertAlmostEqual(budget_control.amount_advance, 400.0)
        self.assertAlmostEqual(budget_control.amount_expense, 0.0)
        self.assertAlmostEqual(budget_control.amount_balance, 2000.0)

        # Make payment full amount = 400
        advance_sheet.action_register_payment()
        f = Form(
            self.env["account.payment.register"].with_context(
                active_model="account.move",
                active_ids=[move.id],
            )
        )
        wizard = f.save()
        wizard.action_create_payments()
        self.assertAlmostEqual(advance_sheet.clearing_residual, 400.0)
        self.assertAlmostEqual(budget_control.amount_advance, 400.0)
        self.assertAlmostEqual(budget_control.amount_expense, 0.0)
        self.assertAlmostEqual(budget_control.amount_balance, 2000.0)

        # Clearing Advance
        user = self.env.ref("base.user_admin")
        with Form(self.env["hr.expense.sheet"]) as clearing:
            clearing.name = "Test Clearing"
            clearing.employee_id = user.employee_id
            clearing.advance_sheet_id = advance_sheet
        clearing_sheet = clearing.save()

        # Change account Expense to KPI, delete tax default and change price to 60.0
        clearing = clearing_sheet.expense_line_ids
        clearing.account_id = self.account_kpi1.id
        clearing.tax_ids = False
        clearing.total_amount = 60.0

        self.assertEqual(clearing_sheet.expense_line_ids.fund_id, self.fund1_g1)
        self.assertEqual(
            clearing_sheet.expense_line_ids.analytic_tag_ids, self.analytic_tag1
        )

        clearing_sheet.action_submit_sheet()
        clearing_sheet.action_approve_expense_sheets()
        self.assertEqual(clearing_sheet.budget_move_ids.fund_id, self.fund1_g1)
        self.assertEqual(
            clearing_sheet.budget_move_ids.analytic_tag_ids, self.analytic_tag1
        )

        self.assertAlmostEqual(advance_sheet.clearing_residual, 400.0)
        self.assertAlmostEqual(budget_control.amount_advance, 340.0)
        self.assertAlmostEqual(budget_control.amount_expense, 60.0)
        self.assertAlmostEqual(budget_control.amount_balance, 2000.0)
