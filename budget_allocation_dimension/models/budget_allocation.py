# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetAllocationLine(models.Model):
    _name = "budget.allocation.line"
    _inherit = ["analytic.dimension.line", "budget.allocation.line"]
    _analytic_tag_field_name = "analytic_tag_ids"

    analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        string="Analytic Tags",
    )
