# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.budget_control.tests.common import BudgetControlCommon


@tagged("post_install", "-at_install")
class TestBudgetControlException(BudgetControlCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.BudgetControlExceptionConfirm = cls.env["budget.control.exception.confirm"]
        # Add group budget in partner
        cls.demo_user = cls.env.ref("base.user_demo")
        cls.partner_assign = cls.demo_user.partner_id
        cls.env.ref("budget_control.group_budget_control_user").write(
            {"users": [(4, cls.demo_user.id)]}
        )
        cls.exception_checkassignee = cls.env.ref(
            "budget_control_exception.bc_excep_assignee_check"
        )
        cls.exception_checkamount = cls.env.ref(
            "budget_control_exception.bc_excep_amount_plan_check"
        )
        # Create sample ready to use Budget Control
        cls.budget_control = cls.BudgetControl.create(
            {
                "name": "CostCenter1/%s" % cls.year,
                "template_id": cls.budget_period.template_id.id,
                "budget_period_id": cls.budget_period.id,
                "analytic_account_id": cls.costcenter1.id,
                "plan_date_range_type_id": cls.date_range_type.id,
                "template_line_ids": [
                    cls.template_line1.id,
                    cls.template_line2.id,
                    cls.template_line3.id,
                ],
            }
        )
        # Test item created for 3 kpi x 4 quarters = 12 budget items
        cls.budget_control.prepare_budget_control_matrix()
        assert len(cls.budget_control.line_ids) == 12
        # # Assign budget.control amount: KPI1 = 100, KPI2=800, Total=300
        # cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi1)[:1].write(
        #     {"amount": 100}
        # )
        # cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi2)[:1].write(
        #     {"amount": 200}
        # )
        # cls.budget_control.flush()  # Need to flush data into table, so it can be sql
        # cls.budget_control.allocated_amount = 300

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
        self.assertEqual(self.budget_control.state, "draft")
        self.budget_control.action_done()
        self.assertEqual(self.budget_control.state, "draft")

        self.budget_control.check_exception_all_draft_orders()
        self.assertEqual(self.budget_control.state, "draft")

        self.budget_control.ignore_exception = True
        self.budget_control.action_done()
        self.assertEqual(self.budget_control.state, "done")
