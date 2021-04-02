# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        compute="_compute_fund_id",
        compute_sudo=True,
        readonly=False,
        store=True,
    )
    fund_all = fields.Many2many(
        comodel_name="budget.source.fund",
        relation="move_line_fund_rel",
        column1="line_id",
        column2="fund_id",
        compute="_compute_fund_all",
        compute_sudo=True,
    )

    @api.depends("analytic_account_id")
    def _compute_fund_id(self):
        for rec in self:
            fund_ids = rec.analytic_account_id.fund_constraint_ids.mapped(
                "fund_id"
            )
            rec.fund_id = len(fund_ids) == 1 and fund_ids.id or False

    @api.depends("analytic_account_id")
    def _compute_fund_all(self):
        for rec in self:
            rec.fund_all = rec.analytic_account_id.fund_constraint_ids.mapped(
                "fund_id"
            )
