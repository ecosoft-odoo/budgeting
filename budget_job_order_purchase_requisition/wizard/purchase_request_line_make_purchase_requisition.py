# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class PurchaseRequestLineMakePurchaseRequisition(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.requisition"

    @api.model
    def _prepare_item(self, line):
        res = super()._prepare_item(line)
        res["job_order_id"] = line.job_order_id.id
        return res

    @api.model
    def _prepare_purchase_requisition_line(self, pr, item):
        res = super()._prepare_purchase_requisition_line(pr, item)
        res["job_order_id"] = item.job_order_id.id
        return res

    @api.model
    def _get_requisition_line_search_domain(self, requisition, item):
        vals = super()._get_requisition_line_search_domain(requisition, item)
        vals.append(("job_order_id", "=", item.job_order_id.id or False))
        return vals


class PurchaseRequestLineMakePurchaseRequisitionItem(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.requisition.item"

    job_order_id = fields.Many2one(
        comodel_name="budget.job.order",
        string="Job Order",
        ondelete="cascade",
    )
