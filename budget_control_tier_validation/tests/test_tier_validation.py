# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from odoo.addons.budget_control.tests.common import get_budget_common_class


@tagged("post_install", "-at_install")
class TestBudgetControlTierValidation(get_budget_common_class()):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()

        # Create a user that will act as the tier reviewer. It needs the
        # budget groups so it can access the budget documents it reviews.
        cls.tier_user = new_test_user(
            cls.env,
            name="Tier User",
            login="tier_user",
            groups=("base.group_system," "budget_control.group_budget_control_manager"),
        )
        cls.tier_def_obj = cls.env["tier.definition"]

        # Create budget plan with 2 analytics (reuse the helper from common).
        # Each plan line gets 2,400.00 so the budget control released amount
        # matches the planning amount.
        lines = [
            Command.create(
                {"analytic_account_id": cls.costcenter1.id, "amount": 2400.0}
            ),
            Command.create(
                {"analytic_account_id": cls.costcenterX.id, "amount": 2400.0}
            ),
        ]
        cls.budget_plan = cls.create_budget_plan(
            cls,
            name="Test - Tier Plan",
            budget_period=cls.budget_period,
            lines=lines,
        )
        # Confirm the plan, create the budget controls and set the plan to
        # done. No tier definition is in place yet, so this is allowed.
        cls.budget_plan.action_confirm()
        cls.budget_plan.action_create_update_budget_control()
        cls.budget_plan.action_done()

        # Refresh data, as budget_control_ids is a computed field cached before
        # the budget controls were created.
        cls.budget_plan.invalidate_recordset()

        # Budget Controls
        cls.budget_control = cls.budget_plan.budget_control_ids[0]
        cls.budget_control2 = cls.budget_plan.budget_control_ids[1]
        for budget_control in (cls.budget_control, cls.budget_control2):
            budget_control.template_line_ids = [
                cls.template_line1.id,
                cls.template_line2.id,
                cls.template_line3.id,
            ]
            # 3 KPIs x 4 quarters = 12 budget items
            budget_control.prepare_budget_control_matrix()
            # KPI1 = 100x4=400, KPI2 = 200x4=800, KPI3 = 300x4=1200 --> 2,400
            budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi1).write(
                {"amount": 100}
            )
            budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi2).write(
                {"amount": 200}
            )
            budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi3).write(
                {"amount": 300}
            )

    def _create_tier_definition(self, model_name, definition_domain="[]"):
        return self.tier_def_obj.create(
            {
                "model_id": self.env["ir.model"]._get(model_name).id,
                "review_type": "individual",
                "reviewer_id": self.tier_user.id,
                "definition_domain": definition_domain,
            }
        )

    def _create_draft_budget_plan(self):
        """Create a fresh budget plan in draft state for plan-tier tests."""
        lines = [
            Command.create(
                {"analytic_account_id": self.costcenter1.id, "amount": 2400.0}
            ),
        ]
        return self.create_budget_plan(
            name="Test - Tier Plan (draft)",
            budget_period=self.budget_period,
            lines=lines,
        )

    def test_01_tier_validation_model_names(self):
        """The three budget models must be registered for tier validation."""
        res = self.tier_def_obj._get_tier_validation_model_names()
        self.assertIn("budget.control", res)
        self.assertIn("budget.plan", res)
        self.assertIn("budget.transfer", res)

    @freeze_time("2001-02-01")
    def test_02_budget_plan_tier_validation(self):
        """Budget plan must be validated before it can be confirmed."""
        self._create_tier_definition("budget.plan")
        budget_plan = self._create_draft_budget_plan().sudo()
        self.assertEqual(budget_plan.state, "draft")

        # Confirming without validation is not allowed
        with self.assertRaises(ValidationError):
            budget_plan.action_confirm()

        # Request validation and approve the tier as the reviewer
        budget_plan.request_validation()
        budget_plan.invalidate_recordset()
        self.assertEqual(budget_plan.validation_status, "waiting")
        budget_plan.with_user(self.tier_user).sudo().validate_tier()
        budget_plan.invalidate_recordset()
        self.assertEqual(budget_plan.validation_status, "validated")

        # Now the plan can be confirmed
        budget_plan.action_confirm()
        self.assertEqual(budget_plan.state, "confirm")

    @freeze_time("2001-02-01")
    def test_03_budget_control_tier_validation(self):
        """Budget control must be validated before it can be controlled."""
        self._create_tier_definition("budget.control")
        budget_control = self.budget_control.sudo()
        self.assertEqual(budget_control.state, "draft")

        # Move to submit state, which is the state_from for tier validation
        budget_control.action_submit()
        self.assertEqual(budget_control.state, "submit")

        # Validating to done without tier review is not allowed
        with self.assertRaises(ValidationError):
            budget_control.action_done()

        # Request validation and approve the tier as the reviewer
        budget_control.request_validation()
        budget_control.invalidate_recordset()
        self.assertEqual(budget_control.validation_status, "waiting")
        budget_control.with_user(self.tier_user).sudo().validate_tier()
        budget_control.invalidate_recordset()
        self.assertEqual(budget_control.validation_status, "validated")

        # Now the budget control can be controlled (done)
        budget_control.action_done()
        self.assertEqual(budget_control.state, "done")

    @freeze_time("2001-02-01")
    def test_04_budget_transfer_tier_validation(self):
        """Budget transfer must be validated before it can be transferred."""
        self._create_tier_definition("budget.transfer")
        # The transfer requires the involved budget controls to be in draft.
        # They are created in draft by setUpClass, so just build the transfer.
        transfer = self._create_budget_transfer(
            budget_from=self.budget_control,
            budget_to=self.budget_control2,
            amount=40.0,
        ).sudo()
        self.assertEqual(transfer.state, "draft")

        transfer.action_submit()
        self.assertEqual(transfer.state, "submit")

        # Transferring without tier review is not allowed
        with self.assertRaises(ValidationError):
            transfer.action_transfer()

        # Request validation and approve the tier as the reviewer
        transfer.request_validation()
        transfer.invalidate_recordset()
        self.assertEqual(transfer.validation_status, "waiting")
        transfer.with_user(self.tier_user).sudo().validate_tier()
        transfer.invalidate_recordset()
        self.assertEqual(transfer.validation_status, "validated")

        # Now the transfer can be applied
        transfer.action_transfer()
        self.assertEqual(transfer.state, "transfer")
