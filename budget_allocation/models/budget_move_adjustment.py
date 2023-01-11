# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetMoveAdjustmentItem(models.Model):
    _name = "budget.move.adjustment.item"
    _inherit = ["analytic.dimension.line", "budget.move.adjustment.item"]
    _analytic_tag_field_name = "analytic_tag_ids"
