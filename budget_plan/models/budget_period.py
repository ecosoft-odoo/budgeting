# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BudgetPeriod(models.Model):
    _inherit = "budget.period"

    control_allocation = fields.Boolean(
        default=True,
        tracking=True,
        help="Block documents that charge an analytic account allocated by "
        "dimension in its budget plan (Details of the plan line), e.g. by "
        "fund, outside its allocations or over them. Unticked, allocations "
        "are for information only.",
    )

    @api.model
    def _check_budget_available(self, controls, budget_period):
        warnings = super()._check_budget_available(controls, budget_period)
        doclines = self.env.context.get("doclines")
        if warnings or not doclines or not budget_period.control_allocation:
            return warnings
        # The budget moves of the controls
        analytic_ids = {control["analytic_id"] for control in controls}
        budget_moves = self._get_control_budget_moves(budget_period, doclines).filtered(
            lambda move: move.analytic_account_id.id in analytic_ids
        )
        return self.env["budget.plan.line.detail"]._check_budget_allocation(
            budget_period, budget_moves
        )
