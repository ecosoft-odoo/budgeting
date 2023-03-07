# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class StockScrap(models.Model):
    _name = "stock.scrap"
    _inherit = [
        "analytic.dimension.line",
        "stock.scrap",
        "budget.docline.mixin.base",
    ]
    _budget_analytic_field = "analytic_account_id"
    _analytic_tag_field_name = "analytic_tag_ids"

    def _prepare_move_values(self):
        res = super()._prepare_move_values()
        res.update({"fund_id": self.fund_id.id})
        # Update stock move line
        res["move_line_ids"][0][2].update({"fund_id": self.fund_id.id})
        return res
