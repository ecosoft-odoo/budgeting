# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
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
    allocation_line = fields.One2many(
        comodel_name="budget.source.fund.allocation",
        inverse_name="budget_control_id",
    )

    @api.depends("allocation_line")
    def _compute_fund_ids(self):
        for rec in self:
            fund_ids = rec.allocation_line.mapped("allocation_id.fund_id")
            rec.write({"fund_ids": [(6, 0, fund_ids.ids)]})

    def _get_amount_available(self):
        self.ensure_one()
        plan_amount = sum(self.item_ids.mapped("amount"))
        fund_amount = sum(self.allocation_line.mapped("amount"))
        return plan_amount, fund_amount

    @api.constrains("item_ids", "allocation_line")
    def _check_fund_amount(self):
        for rec in self:
            plan_amount, fund_amount = rec._get_amount_available()
            currency_id = rec.company_id.currency_id
            if (
                float_compare(
                    plan_amount,
                    fund_amount,
                    precision_rounding=currency_id.rounding,
                )
                == 0
            ):
                raise UserError(
                    _(
                        "you have to plan total amount is equal %.2f%s"
                        % (fund_amount, currency_id.symbol)
                    )
                )
