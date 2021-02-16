# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.tools import float_compare


class BudgetControl(models.Model):
    _inherit = "budget.control"

    fund_ids = fields.Many2many(
        comodel_name="budget.source.fund",
        compute="_compute_fund_ids",
        string="Funds",
    )
    allocation_line = fields.One2many(
        comodel_name="budget.source.fund.allocation",
        inverse_name="budget_control_id",
        copy=True,
    )
    allocated_amount = fields.Monetary(
        compute="_compute_allocated_released_amount",
        store=True,
        help="Total amount source of fund before revision new plan",
    )

    @api.depends("allocation_line")
    def _compute_allocated_released_amount(self):
        for rec in self:
            rec.released_amount = rec.allocated_amount = sum(
                rec.allocation_line.mapped("amount")
            )

    @api.depends("allocation_line")
    def _compute_fund_ids(self):
        for rec in self:
            fund_ids = rec.allocation_line.mapped("allocation_id.fund_id")
            rec.write({"fund_ids": [(6, 0, fund_ids.ids)]})

    def _compare_plan_fund(self, plan_amount, fund_amount):
        """ Check total amount plan have to equal released amount """
        amount_compare = (
            float_compare(
                plan_amount,
                fund_amount,
                precision_rounding=self.currency_id.rounding,
            )
            != 0
        )
        message = _(
            "you have to plan total amount is equal {:,.2f} {}".format(
                fund_amount, self.currency_id.symbol
            )
        )
        return amount_compare, message
