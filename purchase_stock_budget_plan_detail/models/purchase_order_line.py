# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _prepare_stock_moves(self, picking):
        res = super()._prepare_stock_moves(picking)
        for line in res:
            line.update(
                {
                    "fund_id": self.fund_id.id,
                    "analytic_tag_ids": [Command.set(self.analytic_tag_ids.ids)],
                }
            )
        return res
