# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, fields, models


class StockScrap(models.Model):
    _name = "stock.scrap"
    _inherit = [
        "analytic.dimension.line",
        "stock.scrap",
        "budget.docline.mixin.base",
    ]

    analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        string="Analytic Tags",
    )

    def _prepare_move_values(self):
        res = super()._prepare_move_values()
        values_update = {
            "fund_id": self.fund_id.id,
            "analytic_tag_ids": [Command.set(self.analytic_tag_ids.ids)],
        }
        # Update account move line
        res.update(values_update)
        # Update stock move line
        res["move_line_ids"][0][2].update(values_update)
        return res
