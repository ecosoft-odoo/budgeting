# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ast

from freezegun import freeze_time

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.budget_control.tests.common import get_budget_common_class


@tagged("post_install", "-at_install")
class TestBudgetControlRevision(get_budget_common_class()):
    @classmethod
    @freeze_time("2001-04-01 15:00:00")
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

    def test_01_budget_plan_config_auto_cancel(self):
        self.assertEqual(self.env.company.budget_plan_revision_cancel, "manual")
        self.env.company.budget_plan_revision_cancel = "auto"

        self.assertEqual(self.budget_plan.state, "confirm")
        self.budget_plan.action_create_update_budget_control()
        self.budget_plan.action_done()
        self.assertEqual(self.budget_plan.revision_number, 0)
        self.assertTrue(self.budget_plan.init_revision)

        # Refresh data
        self.budget_plan.invalidate_recordset()
        self.budget_control = self.budget_plan.budget_control_ids
        self.assertEqual(self.budget_control.revision_number, 0)
        self.assertTrue(self.budget_control.init_revision)
        self.assertEqual(self.budget_control.state, "draft")
        self.assertTrue(self.budget_control.active)

        # Revision budget plan
        self.budget_plan.action_cancel()
        self.assertEqual(self.budget_plan.state, "cancel")
        action_plan_revision = self.budget_plan.create_revision()

        domain_list = ast.literal_eval(action_plan_revision["domain"])
        plan_new_revision = self.BudgetPlan.browse(domain_list[0][2])

        # Update budget control, it should auto cancel
        plan_new_revision.action_confirm()
        plan_new_revision.action_create_update_budget_control()

        self.budget_control.invalidate_recordset()
        self.assertEqual(self.budget_control.state, "cancel")
        self.assertFalse(self.budget_control.active)

    def test_02_budget_plan_revision_no_budget_control(self):
        """Test budget plan revision without budget control"""
        self.assertEqual(self.budget_plan.state, "confirm")
        self.budget_plan.action_cancel()
        with self.assertRaisesRegex(
            UserError,
            "Cannot revise budget plan that is not related to budget control.",
        ):
            self.budget_plan.create_revision()

    def test_03_budget_plan_revision_with_budget_control(self):
        """Test budget plan revision with budget control"""
        self.assertEqual(self.env.company.budget_plan_revision_cancel, "manual")
        self.assertEqual(self.budget_plan.state, "confirm")
        self.budget_plan.action_create_update_budget_control()
        self.budget_plan.action_done()
        self.assertEqual(self.budget_plan.revision_number, 0)
        self.assertTrue(self.budget_plan.init_revision)

        # Refresh data
        self.budget_plan.invalidate_recordset()
        self.budget_control = self.budget_plan.budget_control_ids
        self.assertEqual(self.budget_control.revision_number, 0)
        self.assertTrue(self.budget_control.init_revision)

        # Test revision budget control is not state cancel
        with self.assertRaisesRegex(
            UserError,
            "Budget control can only be revision when it is in the 'cancel' state.",
        ):
            self.budget_control.action_create_revision()

        # Revision budget plan
        self.budget_plan.action_cancel()
        self.assertEqual(self.budget_plan.state, "cancel")
        action_plan_revision = self.budget_plan.create_revision()

        domain_list = ast.literal_eval(action_plan_revision["domain"])
        plan_new_revision = self.BudgetPlan.browse(domain_list[0][2])

        self.assertEqual(plan_new_revision.revision_number, 1)
        self.assertFalse(plan_new_revision.init_revision)
        self.assertFalse(plan_new_revision.budget_control_ids)

        # Config manual cancel, budget control should error because state is not cancel
        plan_new_revision.action_confirm()
        with self.assertRaisesRegex(
            UserError,
            "In order to create new budget control version, "
            "all current ones must be cancelled.",
        ):
            plan_new_revision.action_create_update_budget_control()

        # Cancel budget control, it should allow update budget control
        self.budget_control.action_cancel()
        self.assertEqual(self.budget_control.state, "cancel")
        plan_new_revision.invalidate_recordset()
        plan_new_revision.action_create_update_budget_control()
        plan_new_revision.invalidate_recordset()
        bc_new_revision = plan_new_revision.budget_control_ids
        self.assertEqual(bc_new_revision.revision_number, 1)
        self.assertFalse(bc_new_revision.init_revision)
        self.assertEqual(bc_new_revision.state, "draft")
        self.assertAlmostEqual(bc_new_revision.amount_budget, 0.0)

    @freeze_time("2001-04-01 15:00:00")
    def test_04_budget_control_revision_lock_amount_current(self):
        """Revision budget control, commitment should normal process"""
        self.assertEqual(self.env.company.budget_plan_revision_cancel, "manual")
        self.assertEqual(self.env.company.budget_control_revision_lock_amount, "none")
        self.env.company.budget_plan_revision_cancel = "auto"
        self.env.company.budget_control_revision_lock_amount = "current"

        self.assertEqual(self.budget_plan.state, "confirm")
        self.budget_plan.action_create_update_budget_control()
        self.budget_plan.action_done()
        self.assertEqual(self.budget_plan.revision_number, 0)
        self.assertTrue(self.budget_plan.init_revision)

        # Refresh data
        self.budget_plan.invalidate_recordset()
        self.budget_control = self.budget_plan.budget_control_ids
        self.assertEqual(self.budget_control.revision_number, 0)
        self.assertTrue(self.budget_control.init_revision)
        self.assertEqual(self.budget_control.state, "draft")
        self.assertTrue(self.budget_control.active)

        self.budget_control.template_line_ids = [
            self.template_line1.id,
            self.template_line2.id,
            self.template_line3.id,
        ]

        # Test item created for 3 kpi x 4 quarters = 12 budget items
        self.budget_control.prepare_budget_control_matrix()

        # Initial Revision, It should editable
        today = fields.Date.today()

        # 2001-01-01 to 2001-03-31
        line1_quarter1 = self.budget_control.line_ids[0]

        self.assertLess(line1_quarter1.date_from, today)
        self.assertLess(line1_quarter1.date_to, today)
        self.assertFalse(line1_quarter1.is_readonly)
        line1_quarter1.amount = 1.0

        # Revision budget plan
        self.budget_plan.action_cancel()
        self.assertEqual(self.budget_plan.state, "cancel")
        action_plan_revision = self.budget_plan.create_revision()

        domain_list = ast.literal_eval(action_plan_revision["domain"])
        plan_new_revision = self.BudgetPlan.browse(domain_list[0][2])

        # Update budget control, it should auto cancel
        plan_new_revision.action_confirm()
        plan_new_revision.action_create_update_budget_control()

        # Refresh data
        plan_new_revision.invalidate_recordset()
        self.budget_control_revision = plan_new_revision.budget_control_ids
        self.assertEqual(self.budget_control_revision.revision_number, 1)
        self.assertFalse(self.budget_control_revision.init_revision)
        self.assertEqual(self.budget_control_revision.state, "draft")
        self.assertTrue(self.budget_control_revision.active)

        self.budget_control_revision.template_line_ids = [
            self.template_line1.id,
            self.template_line2.id,
            self.template_line3.id,
        ]

        # Test item created for 3 kpi x 4 quarters = 12 budget items
        self.budget_control_revision.prepare_budget_control_matrix()
        # 2001-01-01 to 2001-03-31
        line1_quarter1 = self.budget_control_revision.line_ids[0]

        self.assertLess(line1_quarter1.date_from, today)
        self.assertLess(line1_quarter1.date_to, today)
        self.assertTrue(line1_quarter1.is_readonly)
        with self.assertRaisesRegex(UserError, "You can not edit past amount."):
            line1_quarter1.amount = 1.0

        # Config lock amount with previous month
        self.env.company.budget_control_revision_lock_amount = "last"
        line1_quarter1._compute_amount_readonly()
        self.assertTrue(line1_quarter1.is_readonly)
        with self.assertRaisesRegex(UserError, "You can not edit past amount."):
            line1_quarter1.amount = 1.0
