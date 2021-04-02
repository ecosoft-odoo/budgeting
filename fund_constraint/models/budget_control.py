# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    fund_ids = fields.Many2many(
        comodel_name="budget.source.fund",
        compute="_compute_fund_constraint_ids",
    )
    fund_constraint_ids = fields.One2many(
        comodel_name="fund.constraint",
        inverse_name="budget_control_id",
        compute="_compute_fund_constraint_ids",
    )

    @api.depends("analytic_account_id")
    def _compute_fund_constraint_ids(self):
        for rec in self:
            fund_constraint_ids = rec.analytic_account_id.fund_constraint_ids
            rec.fund_constraint_ids = fund_constraint_ids
            rec.fund_ids = fund_constraint_ids.mapped("fund_id")
