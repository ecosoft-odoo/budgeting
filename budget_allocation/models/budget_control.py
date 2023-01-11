# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    allocation_line_ids = fields.One2many(
        comodel_name="budget.allocation.line",
        inverse_name="budget_control_id",
        compute="_compute_allocation_line_ids",
    )

    @api.depends("analytic_account_id")
    def _compute_allocation_line_ids(self):
        for rec in self:
            allocation_line = rec.analytic_account_id.allocation_line_ids.filtered(
                lambda l: l.budget_period_id == self.budget_period_id
            )
            rec.allocation_line_ids = allocation_line
