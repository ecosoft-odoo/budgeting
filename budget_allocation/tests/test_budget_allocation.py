# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

# from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.budget_control.tests.common import BudgetControlCommon


@tagged("post_install", "-at_install")
class TestBudgetAllocation(BudgetControlCommon):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        cls.BudgetAllocation = cls.env[
            "budget.allocation"
        ]  # Create sample activity
        cls.costcenter1.write({"budget_period_id": cls.budget_period.id})
        cls.costcenterX.write({"budget_period_id": cls.budget_period.id})

    @freeze_time("2001-02-01")
    def test_01_create_budget_allocation(self):
        budget_allocation_id = self.BudgetAllocation.create(
            {
                "name": "Budget Allocation 2001",
                "allocation_line_ids": [
                    (
                        0,
                        0,
                        {
                            "analytic_account_id": self.costcenter1.id,
                            "allocated_amount": 10.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "analytic_account_id": self.costcenterX.id,
                            "allocated_amount": 20.0,
                        },
                    ),
                ],
            }
        )
        self.assertEqual(
            budget_allocation_id.budget_period_id, self.budget_period
        )
        self.assertEqual(
            sum(
                budget_allocation_id.allocation_line_ids.mapped(
                    "allocated_amount"
                )
            ),
            budget_allocation_id.total_amount,
        )
        self.assertEqual(
            sum(
                budget_allocation_id.allocation_line_ids.mapped(
                    "released_amount"
                )
            ),
            0.0,
        )
        budget_allocation_id.action_done()
        self.assertEqual(budget_allocation_id.state, "done")
        # After done, amount released must be equal allocated
        self.assertEqual(
            sum(
                budget_allocation_id.allocation_line_ids.mapped(
                    "released_amount"
                )
            ),
            sum(
                budget_allocation_id.allocation_line_ids.mapped(
                    "allocated_amount"
                )
            ),
        )
        # budget plan created by button generate budget plan.
        # initial amount in budget plan update from budget allocation.
        self.assertFalse(budget_allocation_id.plan_id)
        budget_allocation_id.action_generate_budget_plan()
        self.assertTrue(budget_allocation_id.plan_id)
        plan_id = budget_allocation_id.plan_id
        self.assertEqual(
            plan_id.init_amount, budget_allocation_id.total_amount
        )
        # check case edit amount in budget allocation.
        budget_allocation_id.action_draft()
        self.assertEqual(budget_allocation_id.state, "draft")
        budget_allocation_id.allocation_line_ids[0].write(
            {"allocated_amount": 50.0}
        )
        # with Form(budget_allocation_id) as f:
        #     f.allocation_line_ids[0].write({"allocated_amount": 50.0})
        budget_allocation_id._compute_total_amount()
        self.assertEqual(budget_allocation_id.total_amount, 70.0)
        # Initial Amount on Budget Plan and Total Amount Budget Allocation
        # must be equal after state = done
        self.assertNotEqual(
            plan_id.init_amount, budget_allocation_id.total_amount
        )
        with Form(self.env["budget.plan"]):
            plan_id.action_confirm()
        # x=1/0
        # with self.assertRaises(UserError):
        #     plan_id.action_confirm()
        budget_allocation_id.action_done()
        self.assertEqual(
            plan_id.init_amount, budget_allocation_id.total_amount
        )
        self.assertEqual(plan_id.init_amount, plan_id.total_amount)
        self.assertEqual(plan_id.state, "draft")
        plan_id.action_confirm()
        self.assertEqual(plan_id.state, "done")
