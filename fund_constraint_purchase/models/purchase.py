# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ["purchase.order", "base.fund.constraint.commit"]
    _doc_line_field = "order_line"

    def button_confirm(self):
        res = super().button_confirm()
        self.check_fund_constraint()
        return res


class PurchaseOrderLine(models.Model):
    _name = "purchase.order.line"
    _inherit = ["purchase.order.line", "fund.docline.mixin"]
    _fund_analytic_field = "account_analytic_id"
    _amount_balance_field = "price_total"

    @api.depends(_fund_analytic_field)
    def _compute_fund_constraint(self):
        super()._compute_fund_constraint()

    def _prepare_account_move_line(self, move=False):
        self.ensure_one()
        res = super()._prepare_account_move_line(move)
        res["fund_id"] = self.fund_id.id
        return res
