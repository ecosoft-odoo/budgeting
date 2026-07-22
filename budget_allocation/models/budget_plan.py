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
        # Compare against New Budget only: total_amount now also includes
        # Forward Balance, which Budget Allocation has no notion of.
        prec_digits = self.env.user.company_id.currency_id.decimal_places
        if self.state not in ["draft", "cancel"] and any(
            float_compare(
                rec.init_amount, rec.total_new_budget, precision_digits=prec_digits
            )
            != 0
            for rec in self
        ):
            raise UserError(_("Total New Budget is not equal Initial Amount."))

    def unlink(self):
        """Delete budget plan, budget allocation must reset to draft for generate new plan"""
        self.mapped("budget_allocation_id").action_draft()
        return super().unlink()
