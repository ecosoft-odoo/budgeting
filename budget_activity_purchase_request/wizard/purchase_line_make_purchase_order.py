# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    @api.model
    def _prepare_purchase_order_line(self, po, item):
        vals = super()._prepare_purchase_order_line(po, item)
        vals["activity_id"] = item.line_id.activity_id.id
        return vals

    @api.model
    def _get_order_line_search_domain(self, order, item):
        order_line_data = super()._get_order_line_search_domain(order, item)
        order_line_data.append(
            ("activity_id", "=", item.line_id.activity_id.id or False)
        )
        return order_line_data
