# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class StockInventoryLine(models.Model):
    _name = "stock.inventory.line"
    _inherit = [
        "analytic.dimension.line",
        "stock.inventory.line",
        "budget.docline.mixin.base",
    ]
    _analytic_tag_field_name = "analytic_tag_ids"
