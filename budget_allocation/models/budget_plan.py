# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class BudgetPlan(models.Model):
    _inherit = "budget.plan"

    budget_allocation_id = fields.Many2one(
        comodel_name="budget.allocation",
    )
    init_amount = fields.Monetary(
        string="Initial Amount",
        readonly=True,
        help="Initial amount from Budget Allocation",
    )

    @api.constrains("state")
    def _check_amount_initial(self):
        prec_digits = self.env.user.company_id.currency_id.decimal_places
        if self.state not in ["draft", "cancel"] and any(
            float_compare(
                rec.init_amount, rec.total_amount, precision_digits=prec_digits
            )
            != 0
            for rec in self
        ):
            raise UserError(_("Total Amount is not equal Initial Amount."))

    def unlink(self):
        """Delete budget plan, budget allocation must reset to draft for generate new plan"""
        self.mapped("budget_allocation_id").action_draft()
        return super().unlink()
