# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, models


class PurchaseRequestLineMakePurchaseRequisition(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.requisition"

    @api.model
    def _prepare_purchase_requisition_line(self, pr, item):
        res = super()._prepare_purchase_requisition_line(pr, item)
        res["fund_id"] = item.line_id.fund_id.id or False
        res["analytic_tag_ids"] = [Command.set(item.line_id.analytic_tag_ids.ids)]
        return res

    @api.model
    def _get_requisition_line_search_domain(self, requisition, item):
        domain = super()._get_requisition_line_search_domain(requisition, item)
        extra_domain = [
            ("fund_id", "=", item.line_id.fund_id.id or False),
            ("analytic_tag_ids", "in", item.line_id.analytic_tag_ids.ids),
        ]
        return domain + extra_domain
