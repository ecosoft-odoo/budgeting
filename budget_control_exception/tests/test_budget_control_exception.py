# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import Command
from odoo.tests import Form, tagged

from odoo.addons.budget_control.tests.common import get_budget_common_class


@tagged("post_install", "-at_install")
class TestBudgetControlExpense(get_budget_common_class()):
    @classmethod
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
        cls.BudgetControlExceptionConfirm = cls.env["budget.control.exception.confirm"]
        cls.demo_user = cls.env.ref("base.user_demo")
        cls.partner_assign = cls.demo_user.partner_id
        cls.exception_checkassignee = cls.env.ref(
            "budget_control_exception.bc_excep_assignee_check"
        )
        cls.exception_checkamount = cls.env.ref(
            "budget_control_exception.bc_excep_amount_plan_check"
        )

    def _check_normal_process(self):
        self.assertEqual(self.budget_control.state, "draft")
        self.budget_control.action_done()
        self.assertEqual(self.budget_control.state, "done")
        # reset
        self.budget_control.action_draft()

    def test_01_budget_control_exception(self):
        self.exception_checkassignee.active = True
        # Normally Case
        self.budget_control.assignee_id = self.partner_assign.id
        self._check_normal_process()
        # Exception Case
        self.budget_control.assignee_id = False
        self.assertEqual(self.budget_control.state, "draft")
        self.budget_control.action_done()
        self.assertEqual(self.budget_control.state, "draft")

        self.budget_control.check_exception_all_draft_orders()
        self.assertEqual(self.budget_control.state, "draft")
        # Check ignore exception in wizard.
        self.assertFalse(self.budget_control.ignore_exception)
        exception_wiz = self.BudgetControlExceptionConfirm.with_context(
            active_ids=self.budget_control.ids, active_model=self.budget_control._name
        ).create(
            {
                "related_model_id": self.budget_control.id,
            }
        )
        with Form(exception_wiz) as wiz:
            wiz.ignore = True
        exception_wiz.action_confirm()
        self.assertTrue(self.budget_control.ignore_exception)
        self.budget_control.action_done()
        self.assertEqual(self.budget_control.state, "done")

    def test_02_budget_control_line_exception(self):
        self.exception_checkamount.active = True
        # Normally Case
        self.assertTrue(all(plan.amount >= 0 for plan in self.budget_control.line_ids))
        self._check_normal_process()
        # Exception Case
        self.budget_control.line_ids[0].amount = -1
        total_amount = sum(self.budget_control.line_ids.mapped("amount"))
        self.budget_control.released_amount = total_amount

        self.assertEqual(self.budget_control.state, "draft")
        self.budget_control.action_done()
        self.assertEqual(self.budget_control.state, "draft")

        self.budget_control.check_exception_all_draft_orders()
        self.assertEqual(self.budget_control.state, "draft")

        self.budget_control.ignore_exception = True
        self.budget_control.action_done()
        self.assertEqual(self.budget_control.state, "done")
