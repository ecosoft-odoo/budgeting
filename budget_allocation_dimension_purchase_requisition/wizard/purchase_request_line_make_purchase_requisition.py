# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class PurchaseRequestLineMakePurchaseRequisition(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.requisition"

    @api.model
    def _prepare_purchase_requisition_line(self, pr, item):
        """Convert analytic_tags from [1,2,3] to [6, 0, [1,2,3]]"""
        pr_line_dict = super()._prepare_purchase_requisition_line(pr, item)
        pr_line_dict["analytic_tag_ids"] = [(6, 0, pr_line_dict["analytic_tag_ids"])]
        return pr_line_dict
