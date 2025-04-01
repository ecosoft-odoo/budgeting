# Copyright 2020 Ecosoft - (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, fields, models


class BudgetPlanAnalyticSelect(models.TransientModel):
    _name = "budget.plan.analytic.select"
    _description = "Select analytic account"

    analytic_account_ids = fields.Many2many(
        comodel_name="account.analytic.account",
    )
    company_ids = fields.Many2many(
        comodel_name="res.company",
    )

    def _prepare_plan_lines(self):
        plan_lines = [
            Command.create({"analytic_account_id": aa.id})
            for aa in self.analytic_account_ids
        ]
        return plan_lines

    def action_add(self):
        active_id = self.env.context.get("active_id")
        plan = self.env["budget.plan"].browse(active_id)
        if not plan:
            return

        # Clear all lines
        plan.line_ids.unlink()

        if not self.analytic_account_ids:
            return

        # Add lines
        plan_lines = self._prepare_plan_lines()
        return plan.write({"line_ids": plan_lines})
