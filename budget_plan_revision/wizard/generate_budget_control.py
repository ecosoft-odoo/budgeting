# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class GenerateBudgetControl(models.TransientModel):
    _inherit = "generate.budget.control"

    def _hook_budget_controls(self, budget_controls):
        """ Update budget control for case new budget in year """
        budget_controls = super()._hook_budget_controls(budget_controls)
        model = self._context.get("active_model", False)
        revision_number = self._context.get("revision_number", False)
        init_revision = self._context.get("init_revision", False)
        if model == "budget.plan" and revision_number:
            budget_controls.write(
                {
                    "revision_number": revision_number,
                    "init_revision": init_revision,
                }
            )
        return budget_controls

    def _get_existing_budget(self):
        self = self.with_context(active_test=False)
        existing_budget_controls = super()._get_existing_budget()
        BudgetControl = self.env["budget.control"]
        plan_line_revision = self._context.get("plan_line_revision", False)
        if plan_line_revision:
            existing_budget_controls = BudgetControl.search(
                [
                    ("budget_id", "=", self.budget_id.id),
                    (
                        "analytic_account_id",
                        "in",
                        plan_line_revision.mapped("analytic_account_id").ids,
                    ),
                ]
            )
        return existing_budget_controls
