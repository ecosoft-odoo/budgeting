# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    allocated_amount = fields.Monetary(
        compute="_compute_allocated_released_amount",
        store=True,
        help="Total amount source of fund before revision new plan",
    )
    released_amount = fields.Monetary(
        compute="_compute_allocated_released_amount",
        store=True,
        help="Total amount source of fund current (include transfer amount)",
    )

    @api.depends("allocation_line")
    def _compute_allocated_released_amount(self):
        for rec in self:
            rec.released_amount = rec.allocated_amount = sum(
                rec.allocation_line.mapped("amount")
            )

    def _get_amount_available(self):
        """ Change fund amount constrain to released amount """
        self.ensure_one()
        plan_amount, fund_amount = super()._get_amount_available()
        fund_amount = self.released_amount
        return plan_amount, fund_amount
