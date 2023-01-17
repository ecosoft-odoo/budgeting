# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ast

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.budget_control.tests.common import BudgetControlCommon


@tagged("post_install", "-at_install")
class TestBudgetPlanRevision(BudgetControlCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.BudgetPlan = cls.env["budget.plan"]
        # Create sample ready to use Budget Control
        cls.budget_control = cls.BudgetControl.create(
            {
                "name": "CostCenter1/2002",
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
        # Assign budget.control amount: KPI1 = 100, KPI2=200, Total=300
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi1)[:1].write(
            {"amount": 100}
        )
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi2)[:1].write(
            {"amount": 200}
        )
        cls.budget_control.flush()  # Need to flush data into table, so it can be sql
        cls.budget_control.allocated_amount = 300
        cls.budget_control.action_done()

    @freeze_time("2001-02-01")
    def test_01_revision_budget_plan(self):
        """
        Test normal process create budget plan
        """
        budget_plan = self.BudgetPlan.create(
            {
                "name": "Budget Plan Test {}".format(self.year),
                "budget_period_id": self.budget_period.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "analytic_account_id": self.costcenter1.id,
                            "amount": 100.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "analytic_account_id": self.costcenterX.id,
                            "amount": 200.0,
                        },
                    ),
                ],
            }
        )
        budget_plan.action_confirm()
        # Analytic has 1 budget control from create manual
        self.assertEqual(len(budget_plan.line_ids[0].budget_control_ids), 1)
        self.assertFalse(len(budget_plan.line_ids[1].budget_control_ids))
        # Archive budget control created before plan
        self.budget_control.active = False
        self.assertFalse(budget_plan.line_ids[0].budget_control_ids)
        # Create budget controls
        budget_plan.action_create_update_budget_control()
        self.assertEqual(len(budget_plan.line_ids[0].budget_control_ids), 1)
        self.assertEqual(len(budget_plan.line_ids[1].budget_control_ids), 1)
        budget_plan.action_done()
        # Check revision plan, control is 0 (initial)
        self.assertEqual(budget_plan.revision_number, 0)
        self.assertTrue(budget_plan.init_revision)
        self.assertEqual(budget_plan.line_ids[0].budget_control_ids.revision_number, 0)
        new_plan_val = budget_plan.create_revision()
        self.assertFalse(budget_plan.active)
        domain_list = ast.literal_eval(new_plan_val["domain"])
        new_budget_plan = self.BudgetPlan.browse(domain_list[0][2])
        self.assertTrue(new_budget_plan.active)
        self.assertEqual(new_budget_plan.revision_number, 1)
        self.assertFalse(new_budget_plan.init_revision)
        self.assertFalse(new_budget_plan.line_ids[0].budget_control_ids)
        self.assertFalse(new_budget_plan.line_ids[1].budget_control_ids)
        new_budget_plan.action_confirm()
        # Can't new revision if not created budget control
        with self.assertRaises(UserError):
            new_budget_plan.create_revision()
        # Can't create/update budget control previous if not state 'cancel'
        with self.assertRaises(UserError):
            new_budget_plan.action_create_update_budget_control()
        # Cancel all budget control
        budget_plan.budget_control_ids.action_cancel()
        # Create budget controls
        new_budget_plan.action_create_update_budget_control()
        self.assertEqual(len(new_budget_plan.line_ids[0].budget_control_ids), 1)
        self.assertEqual(len(new_budget_plan.line_ids[1].budget_control_ids), 1)
        # budget control will create revision following budget plan
        self.assertEqual(
            new_budget_plan.line_ids[0].budget_control_ids.revision_number, 1
        )
        self.assertEqual(
            new_budget_plan.line_ids[1].budget_control_ids.revision_number, 1
        )
