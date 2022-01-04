# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class AccountPaymentDeduction(models.TransientModel):
    _inherit = "account.payment.deduction"

    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        string="Fund",
        index=True,
        domain="[('id', 'in', fund_all)]",
    )
    fund_all = fields.Many2many(
        comodel_name="budget.source.fund",
        compute="_compute_fund_all",
        compute_sudo=True,
    )

    @api.onchange("fund_all")
    def _onchange_fund_all(self):
        for rec in self:
            rec.fund_id = (
                rec.fund_all._origin.id if len(rec.fund_all) == 1 else False
            )

    @api.depends("analytic_account_id")
    def _compute_fund_all(self):
        for rec in self:
            rec.fund_all = rec.analytic_account_id.allocation_line_ids.mapped("fund_id")
