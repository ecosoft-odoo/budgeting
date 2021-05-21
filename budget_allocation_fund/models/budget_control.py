# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    fund_ids = fields.Many2many(
        comodel_name="budget.source.fund",
        compute="_compute_allocation_line_ids",
    )

    @api.depends("analytic_account_id")
    def _compute_allocation_line_ids(self):
        res = super()._compute_allocation_line_ids()
        for rec in self:
            rec.fund_ids = rec.allocation_line_ids.mapped("fund_id")
        return res
