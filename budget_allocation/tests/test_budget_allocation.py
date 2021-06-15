# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo.exceptions import UserError
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
        cls.AnalyticAccount = cls.env["account.analytic.account"]
        cls.AllocationLine = cls.env["budget.allocation.line"]
        cls.BudgetPlan = cls.env["budget.plan"]
        cls.budget_control_ids = False
        cls.costcenter1.write({"budget_period_id": cls.budget_period.id})
        cls.costcenterX.write({"budget_period_id": cls.budget_period.id})

    def _create_budget_allocation(self, analytic_account, amount):
        budget_allocation_id = self.BudgetAllocation.create(
            {
                "name": "Budget Allocation {}".format(
                    self.budget_period.display_name
                ),
                "allocation_line_ids": [
                    (
                        0,
                        0,
                        {
                            "analytic_account_id": analytic.id,
                            "allocated_amount": amount,
                        },
                    )
                    for analytic in analytic_account
                ],
            }
        )
        return budget_allocation_id

    @freeze_time("2001-02-01")
    def test_01_process_budget_allocation(self):
        analytic_account = self.costcenter1 + self.costcenterX
        amount = 100.0
        budget_allocation_id = self._create_budget_allocation(
            analytic_account, amount
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
        # Open Analytic with depend on date period, Check count analytic
        analytic_dict = budget_allocation_id.button_open_analytic()
        analytic_all = self.AnalyticAccount.search(analytic_dict["domain"])
        analytic_check = self.AnalyticAccount.search(
            [
                (
                    "bm_date_to",
                    ">=",
                    budget_allocation_id.budget_period_id.bm_date_from,
                ),
                (
                    "bm_date_from",
                    "<=",
                    budget_allocation_id.budget_period_id.bm_date_to,
                ),
            ]
        )
        self.assertEqual(analytic_all, analytic_check)
        # Open Allocation Line, Check count line is correct
        allocation_line_dict = budget_allocation_id.button_open_allocation()
        allocation_line = self.AllocationLine.search(
            allocation_line_dict["domain"]
        )
        self.assertEqual(len(allocation_line), len(analytic_account))
        budget_allocation_id.action_cancel()
        self.assertEqual(budget_allocation_id.state, "cancel")
        budget_allocation_id.action_draft()
        self.assertEqual(budget_allocation_id.state, "draft")
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
        # Check smart button link and plan_id must be equal.
        plan_dict = budget_allocation_id.button_open_budget_plan()
        plan = self.BudgetPlan.browse(plan_dict["res_id"])
        plan_id = budget_allocation_id.plan_id
        self.assertEqual(plan, plan_id)
        self.assertEqual(
            plan_id.init_amount, budget_allocation_id.total_amount
        )
        # Check case edit amount in budget allocation.
        budget_allocation_id.action_draft()
        with Form(budget_allocation_id.allocation_line_ids[0]) as f:
            f.allocated_amount = 50.0
        self.assertEqual(budget_allocation_id.total_amount, amount + 50.0)
        # Initial Amount in Budget Plan and
        # Total Amount in Budget Allocation must be equal after state = done
        self.assertNotEqual(
            plan_id.init_amount, budget_allocation_id.total_amount
        )
        self.assertEqual(plan_id.init_amount, plan_id.total_amount)
        budget_allocation_id.action_done()
        self.assertEqual(
            plan_id.init_amount, budget_allocation_id.total_amount
        )
        self.assertNotEqual(plan_id.init_amount, plan_id.total_amount)
        with self.assertRaises(UserError):
            plan_id.action_confirm()
        # Update plan from budget allocation
        plan_id.action_generate_plan()
        self.assertEqual(plan_id.init_amount, plan_id.total_amount)
        self.assertEqual(plan_id.state, "draft")
        plan_id.action_confirm()
        self.assertEqual(plan_id.state, "confirm")
        # Check budget control and plan line must be the same.
        plan_id.action_create_update_budget_control()
        self.assertEqual(
            len(plan_id.plan_line), len(plan_id.budget_control_ids)
        )
        plan_id.action_done()
        self.assertEqual(plan_id.state, "done")
        budget_control_ids = plan_id.budget_control_ids
        self.assertEqual(
            budget_control_ids.mapped("allocation_line_ids"),
            budget_allocation_id.allocation_line_ids,
        )
        return budget_control_ids

    @freeze_time("2001-02-01")
    def test_02_commitment_bill(self):
        # budget control is depends on budget allocation
        budget_control_ids = self.test_01_process_budget_allocation()
        # Test with 1 budget control, it can commit budget not over 50
        budget_control = budget_control_ids[0]
        self.assertEqual(
            budget_control.allocation_line_ids.allocated_amount, 50
        )
        budget_control.write(
            {
                "kpi_ids": [self.kpi1.id, self.kpi2.id, self.kpi3.id],
            }
        )
        # Test item created for 3 kpi x 4 quarters = 12 budget items
        budget_control.prepare_budget_control_matrix()
        assert len(budget_control.item_ids) == 12
        # Assign budget.control amount: KPI1 = 100x4=400, KPI2=800, KPI3=1,200
        budget_control.item_ids.filtered(
            lambda x: x.kpi_expression_id == self.kpi1.expression_ids[0]
        ).write({"amount": 100})
        budget_control.item_ids.filtered(
            lambda x: x.kpi_expression_id == self.kpi2.expression_ids[0]
        ).write({"amount": 200})
        budget_control.item_ids.filtered(
            lambda x: x.kpi_expression_id == self.kpi3.expression_ids[0]
        ).write({"amount": 300})
        # KPI spent over limit budget allocation -> lock
        bill1 = self._create_simple_bill(
            self.costcenter1, self.account_kpiX, 100
        )
        with self.assertRaises(UserError):
            bill1.action_post()
        bill1.button_draft()
        # KPI commit less than allocated amount.
        bill2 = self._create_simple_bill(
            self.costcenter1, self.account_kpiX, 40
        )
        bill2.action_post()
        # KPI commit 40 already, it can commit not over 10
        bill3 = self._create_simple_bill(
            self.costcenter1, self.account_kpiX, 30
        )
        with self.assertRaises(UserError):
            bill3.action_post()
        bill3.button_draft()
