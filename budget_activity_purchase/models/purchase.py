# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _prepare_account_move_line(self, move=False):
        self.ensure_one()
        res = super()._prepare_account_move_line(move)
        res["activity_id"] = self.activity_id.id
        return res

    def _get_po_line_account(self):
        if self.activity_id:
            return self.activity_id.account_id
        return super()._get_po_line_account()
