# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    @api.model
    def _prepare_purchase_order_line(self, po, item):
        vals = super()._prepare_purchase_order_line(po, item)
        vals["fund_id"] = item.fund_id.id
        return vals

    @api.model
    def _prepare_item(self, line):
        vals = super()._prepare_item(line)
        vals["fund_id"] = line.fund_id.id
        return vals

    @api.model
    def _get_order_line_search_domain(self, order, item):
        order_line_data = super()._get_order_line_search_domain(order, item)
        order_line_data.append(("fund_id", "=", item.fund_id.id))
        return order_line_data


class PurchaseRequestLineMakePurchaseOrderItem(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order.item"

    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        string="Fund",
    )
