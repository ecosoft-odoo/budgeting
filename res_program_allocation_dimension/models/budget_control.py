# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        string="Analytic Tags",
        compute="_compute_analytic_tag_ids",
    )

    @api.depends("analytic_account_id")
    def _compute_analytic_tag_ids(self):
        for rec in self:
            rec.analytic_tag_ids = rec.fund_constraint_ids.mapped(
                "analytic_tag_ids"
            )
