# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class GenerateBudgetControl(models.TransientModel):
    _inherit = "generate.budget.control"

    plan_manual = fields.Boolean(
        string="Manual Plan",
        default=True,
    )

    def _create_budget_controls(self, vals):
        ctx = self._context.copy()
        if self.plan_manual:
            ctx["plan_manual"] = True
        budget_controls = super(
            GenerateBudgetControl, self.with_context(ctx)
        )._create_budget_controls(vals)
        return budget_controls
