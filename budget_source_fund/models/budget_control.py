# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class BudgetControl(models.Model):
    _inherit = "budget.control"

    fund_ids = fields.Many2many(
        comodel_name="budget.source.fund",
        compute="_compute_fund_ids",
        string="Funds",
    )
    fund_line_ids = fields.One2many(
        comodel_name="budget.source.fund.line",
        inverse_name="budget_control_id",
    )

    @api.depends("fund_line_ids")
    def _compute_fund_ids(self):
        for rec in self:
            rec.fund_ids = rec.fund_line_ids.mapped("fund_id").ids

    @api.constrains("item_ids", "fund_line_ids")
    def _check_fund_amount(self):
        for rec in self:
            plan_amount = sum(rec.item_ids.mapped("amount"))
            fund_amount = sum(rec.fund_line_ids.mapped("amount"))
            currency_id = rec.company_id.currency_id
            if (
                float_compare(
                    plan_amount,
                    fund_amount,
                    precision_rounding=currency_id.rounding,
                )
                == 1
            ):
                raise UserError(
                    _(
                        "you can plan total amount not more than %.2f%s"
                        % (fund_amount, currency_id.symbol)
                    )
                )
