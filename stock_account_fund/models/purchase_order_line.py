# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _prepare_stock_moves(self, picking):
        res = super()._prepare_stock_moves(picking)
        for line in res:
            self.fund_id and line.update({"fund_id": self.fund_id.id}) or False
        return res
