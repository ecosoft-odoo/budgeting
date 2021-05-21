# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"
    _amount_balance_field = "price_total"

    def _prepare_account_move_line(self, move=False):
        res = super()._prepare_account_move_line(move)
        res["fund_id"] = self.fund_id.id
        return res

    # Trigger analytic
    @api.depends("account_analytic_id")
    def _compute_fund_all(self):
        super()._compute_fund_all()
