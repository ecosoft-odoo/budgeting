# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    fund_ids = fields.Many2many(
        comodel_name="budget.source.fund",
        compute="_compute_fund_constraint",
    )
    fund_constraint = fields.One2many(
        comodel_name="fund.constraint",
        inverse_name="budget_control_id",
        compute="_compute_fund_constraint",
    )

    @api.depends("analytic_account_id")
    def _compute_fund_constraint(self):
        for rec in self:
            fund_constraint = rec.analytic_account_id.fund_constraint
            rec.fund_constraint = fund_constraint
            rec.fund_ids = fund_constraint.mapped("fund_id")
