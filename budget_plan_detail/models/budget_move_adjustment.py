# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetMoveAdjustmentItem(models.Model):
    _name = "budget.move.adjustment.item"
    _inherit = ["analytic.dimension.line", "budget.move.adjustment.item"]

    analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        string="Analytic Tags",
    )
