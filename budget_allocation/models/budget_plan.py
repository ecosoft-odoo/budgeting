# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class BudgetPlan(models.Model):
    _inherit = "budget.plan"

    budget_allocation_id = fields.Many2one(comodel_name="budget.allocation")
    init_amount = fields.Monetary(
        string="Initial Amount",
        readonly=True,
        help="Initial amount from Budget Allocation",
    )
    total_new_budget = fields.Monetary(
        compute="_compute_total_new_budget",
        help="Sum of plan lines' New Budget, excluding Forward Balance.",
    )

    @api.depends("line_ids.amount")
    def _compute_total_new_budget(self):
        for rec in self:
            rec.total_new_budget = sum(rec.line_ids.mapped("amount"))

    @api.constrains("state")
    def _check_amount_initial(self):
        for rec in self:
            if rec.state in ["draft", "cancel"] or not rec.budget_allocation_id:
                continue
            prec_digits = rec.currency_id.decimal_places
            if rec.budget_allocation_id.amount_basis == "allocated":
                analytic_ids = set(
                    rec.budget_allocation_id.line_ids.mapped("analytic_account_id").ids
                )
                plan_total = sum(
                    line.allocated_amount
                    for line in rec.line_ids
                    if line.analytic_account_id.id in analytic_ids
                )
                amount_label = _("Total Allocated")
            else:
                plan_total = rec.total_new_budget
                amount_label = _("Total New Budget")
            if (
                float_compare(rec.init_amount, plan_total, precision_digits=prec_digits)
                != 0
            ):
                raise UserError(_("%s is not equal to Initial Amount.") % amount_label)

    def unlink(self):
        """Delete budget plan, budget allocation must reset to draft for generate new plan"""
        self.mapped("budget_allocation_id").action_draft()
        return super().unlink()
