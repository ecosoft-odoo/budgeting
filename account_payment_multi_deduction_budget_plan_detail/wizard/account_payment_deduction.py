# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class AccountPaymentDeduction(models.TransientModel):
    _name = "account.payment.deduction"
    _inherit = [
        "analytic.dimension.line",
        "account.payment.deduction",
    ]
    _analytic_tag_field_name = "writeoff_analytic_tag_ids"

    writeoff_fund_all = fields.Many2many(comodel_name="budget.source.fund")
    writeoff_fund_id = fields.Many2one(comodel_name="budget.source.fund", string="Fund")
    writeoff_analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        relation="account_payment_deduction_tag_rel",
        column1="register_id",
        column2="tag_id",
        string="Analytic Tag",
    )
    writeoff_analytic_tag_all = fields.Many2many(
        comodel_name="account.analytic.tag",
        relation="account_payment_deduction_tag_all_rel",
        column1="register_id",
        column2="tag_all_id",
    )

    @api.onchange("analytic_distribution")
    def _onchange_budget_all(self):
        Analytic = self.env["account.analytic.account"]
        for rec in self:
            if not rec.analytic_distribution:
                continue

            account_analytic_ids = [
                int(v) for k in rec.analytic_distribution.keys() for v in k.split(",")
            ]
            analytics = Analytic.browse(account_analytic_ids)
            plan_lines = analytics.mapped("plan_line_detail_ids")
            rec.writeoff_fund_all = plan_lines.mapped("fund_id")
            rec.writeoff_fund_id = (
                rec.writeoff_fund_all._origin.id
                if len(rec.writeoff_fund_all) == 1
                else False
            )
            rec.writeoff_analytic_tag_all = plan_lines.mapped("analytic_tag_ids")
