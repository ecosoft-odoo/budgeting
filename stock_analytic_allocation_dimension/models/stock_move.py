# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = [
        "analytic.dimension.line",
        "stock.move",
        "budget.docline.mixin.base",
    ]
    _analytic_tag_field_name = "analytic_tag_ids"
