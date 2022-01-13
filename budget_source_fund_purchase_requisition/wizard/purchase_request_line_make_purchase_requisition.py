# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class PurchaseRequestLineMakePurchaseRequisition(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.requisition"

    @api.model
    def _prepare_item(self, line):
        res = super()._prepare_item(line)
        res["fund_id"] = line.fund_id.id
        return res

    @api.model
    def _prepare_purchase_requisition_line(self, pr, item):
        res = super()._prepare_purchase_requisition_line(pr, item)
        res["fund_id"] = item.fund_id.id
        return res

    @api.model
    def _get_requisition_line_search_domain(self, requisition, item):
        vals = super()._get_requisition_line_search_domain(requisition, item)
        vals.append(("fund_id", "=", item.fund_id.id or False))
        return vals


class PurchaseRequestLineMakePurchaseRequisitionItem(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.requisition.item"

    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        string="Fund",
        ondelete="cascade",
    )
