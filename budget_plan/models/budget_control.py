# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    budget_plan_id = fields.Many2one(
        comodel_name="budget.plan",
        index=True,
        copy=False,
        ondelete="restrict",
        tracking=True,
        help="Budget Plan that owns and manages this control's allocated amount.",
    )
    allocation_ids = fields.Many2many(
        comodel_name="budget.plan.line.detail",
        string="Allocations",
        compute="_compute_allocation_ids",
        compute_sudo=True,
        help="Allocation of the budget by dimension, e.g. by fund, in the plan "
        "managing this sheet.",
    )

    @api.depends(
        "analytic_account_id",
        "budget_plan_id.state",
        "budget_plan_id.line_ids.detail_ids",
    )
    def _compute_allocation_ids(self):
        for control in self:
            control.allocation_ids = control._get_budget_allocations()

    def _get_budget_allocations(self):
        """Details of the analytic account in the plan managing this sheet,
        also while the plan is set to draft to revise them."""
        self.ensure_one()
        plan = self.budget_plan_id.filtered(lambda plan: plan.state != "cancel")
        return plan.line_ids.filtered(
            lambda line: line.analytic_account_id == self.analytic_account_id
        ).detail_ids

    def action_view_budget_plan(self):
        self.ensure_one()
        return self.budget_plan_id._get_records_action(name=self.env._("Budget Plan"))
