# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class GenerateBudgetControl(models.TransientModel):
    _inherit = "generate.budget.control"

    def _hook_budget_controls(self, budget_controls):
        budget_controls = super()._hook_budget_controls(budget_controls)
        model = self._context.get("active_model", False)
        revision = self._context.get("revision", False)
        if model == "budget.plan" and revision:
            budget_controls.write(
                {
                    "revision_number": revision,
                }
            )
        return budget_controls
