# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_confirm(self):
        res = super().button_confirm()
        for doc in self:
            po_line = doc.order_line.filtered("fund_id")
            for line in po_line:
                line.check_fund_constraint()
        return res


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"
    _amount_balance_field = "price_total"

    @api.depends("account_analytic_id")
    def _compute_fund_constraint(self):
        super()._compute_fund_constraint()

    def _prepare_account_move_line(self, move=False):
        self.ensure_one()
        res = super()._prepare_account_move_line(move)
        res["fund_id"] = self.fund_id.id
        return res
