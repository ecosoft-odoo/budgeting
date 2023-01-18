# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ast

from freezegun import freeze_time

from odoo.tests import tagged

from odoo.addons.budget_allocation.tests.test_budget_allocation import (
    TestBudgetAllocation,
)


@tagged("post_install", "-at_install")
class TestBudgetAllocationRevision(TestBudgetAllocation):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @freeze_time("2001-02-01")
    def test_01_revision_budget_allocation(self):
        amount = 100.0
        budget_allocation_id = self._create_budget_allocation(amount)
        self.assertTrue(budget_allocation_id.init_revision)
        self.assertEqual(budget_allocation_id.revision_number, 0)
        budget_allocation_id.action_done()
        budget_plan = budget_allocation_id.plan_id
        self.assertTrue(budget_plan.init_revision)
        self.assertEqual(budget_plan.revision_number, 0)
        budget_plan.action_confirm()
        # Create budget control sheet
        budget_plan.action_create_update_budget_control()
        self.assertEqual(len(budget_plan.line_ids[0].budget_control_ids), 1)
        self.assertEqual(len(budget_plan.line_ids[1].budget_control_ids), 1)
        budget_allocation_id.action_cancel()
        # Revision budget allocation
        new_allocation_val = budget_allocation_id.create_revision()
        domain_list = ast.literal_eval(new_allocation_val["domain"])
        new_budget_allocation = self.BudgetAllocation.browse(domain_list[0][2])
        self.assertFalse(new_budget_allocation.init_revision)
        self.assertEqual(new_budget_allocation.revision_number, 1)
        self.assertEqual(new_budget_allocation.state, "draft")
        self.assertFalse(budget_allocation_id.active)
        new_budget_allocation.action_done()
        new_budget_plan = new_budget_allocation.plan_id
        self.assertNotEqual(new_budget_plan, budget_plan)
        self.assertEqual(new_budget_plan.revision_number, 1)
