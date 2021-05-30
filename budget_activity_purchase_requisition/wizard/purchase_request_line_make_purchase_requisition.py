# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class PurchaseRequestLineMakePurchaseRequisition(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.requisition"

    @api.model
    def _prepare_item(self, line):
        res = super()._prepare_item(line)
        res["activity_id"] = line.activity_id.id
        return res

    @api.model
    def _prepare_purchase_requisition_line(self, pr, item):
        res = super()._prepare_purchase_requisition_line(pr, item)
        res["activity_id"] = item.activity_id.id
        return res

    @api.model
    def _get_requisition_line_search_domain(self, requisition, item):
        vals = super()._get_requisition_line_search_domain(requisition, item)
        vals.append(("activity_id", "=", item.activity_id.id or False))
        return vals


class PurchaseRequestLineMakePurchaseRequisitionItem(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.requisition.item"

    activity_id = fields.Many2one(
        comodel_name="budget.activity",
        string="Activity",
        ondelete="cascade",
    )
