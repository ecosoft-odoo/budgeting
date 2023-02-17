# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountAsset(models.Model):
    _inherit = "account.asset"

    not_affect_budget = fields.Boolean(default=True)
    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        index=True,
        ondelete="restrict",
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
            rec.fund_id = rec.fund_all._origin.id if len(rec.fund_all) == 1 else False

    @api.depends("account_analytic_id")
    def _compute_fund_all(self):
        SourceFund = self.env["budget.source.fund"]
        source_fund_all = SourceFund.search([])
        allocation_line = hasattr(
            self.env["account.analytic.account"], "allocation_line_ids"
        )
        allocation_line_fund = hasattr(self.env["budget.allocation.line"], "fund_id")
        for rec in self:
            # show all fund, when not install 'budget_allocation_fund' module
            rec.fund_all = (
                rec.account_analytic_id.allocation_line_ids.mapped("fund_id")
                if allocation_line and allocation_line_fund
                else source_fund_all
            )
