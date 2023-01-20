# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class PurchaseRequestLineMakePurchaseRequisition(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.requisition"

    @api.model
    def _prepare_purchase_requisition_line(self, pr, item):
        """Use Purchase Request analytic carry forward commit, if it already forward."""
        pr_line_dict = super()._prepare_purchase_requisition_line(pr, item)
        if item.line_id.fwd_analytic_account_id:
            pr_line_dict[
                "account_analytic_id"
            ] = item.line_id.fwd_analytic_account_id.id
        return pr_line_dict
