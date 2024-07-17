# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class PurchaseRequestLineMakePurchaseRequisition(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.requisition"

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        pr_line_obj = self.env["purchase.request.line"]
        for item in res["item_ids"]:
            pr_line = pr_line_obj.browse(item[2]["line_id"])
            item[2]["date_commit"] = pr_line.date_commit
        return res

    @api.model
    def _prepare_purchase_requisition_line(self, pr, item):
        """Use Purchase Request analytic carry forward commit, if it already forward."""
        pr_line_dict = super()._prepare_purchase_requisition_line(pr, item)
        pr_line_dict["date_commit"] = item.line_id.date_commit
        return pr_line_dict

    @api.model
    def _get_requisition_line_search_domain(self, requisition, item):
        # No merge line, if date_commit is different
        vals = super()._get_requisition_line_search_domain(requisition, item)
        vals.append(("date_commit", "=", item.line_id.date_commit))
        return vals


class PurchaseRequestLineMakePurchaseRequisitionItem(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.requisition.item"

    date_commit = fields.Date(readonly=True)
