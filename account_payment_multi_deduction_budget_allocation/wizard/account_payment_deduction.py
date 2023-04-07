# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class AccountPaymentDeduction(models.TransientModel):
    _name = "account.payment.deduction"
    _inherit = [
        "analytic.dimension.line",
        "account.payment.deduction",
    ]

    writeoff_fund_all = fields.Many2many(comodel_name="budget.source.fund")
    writeoff_fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        string="Fund",
        index=True,
        tracking=True,
        ondelete="restrict",
        domain="[('id', 'in', writeoff_fund_all)]",
    )
    writeoff_analytic_tag_all = fields.Many2many(
        comodel_name="account.analytic.tag",
        relation="account_payment_deduction_tag_all_rel",
        column1="register_id",
        column2="tag_all_id",
    )

    @api.onchange("analytic_account_id")
    def _onchange_budget_all(self):
        for rec in self:
            allocation_lines = rec.analytic_account_id.allocation_line_ids
            rec.writeoff_fund_all = allocation_lines.mapped("fund_id")
            rec.writeoff_fund_id = (
                rec.writeoff_fund_all._origin.id
                if len(rec.writeoff_fund_all) == 1
                else False
            )
            rec.writeoff_analytic_tag_all = allocation_lines.mapped("analytic_tag_ids")

    @api.depends("payment_id")
    def _compute_analytic_multi_deduction(self):
        res = super()._compute_analytic_multi_deduction()
        self._onchange_budget_all()
        return res
