# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class PurchaseRequisitionLine(models.Model):
    _name = "purchase.requisition.line"
    _inherit = [
        "budget.docline.mixin.base",
        "purchase.requisition.line",
    ]

    def _prepare_purchase_order_line(
        self, name, product_qty=0.0, price_unit=0.0, taxes_ids=False
    ):
        """Send activity_id from TE to RFQ"""
        res = super()._prepare_purchase_order_line(
            name,
            product_qty=product_qty,
            price_unit=price_unit,
            taxes_ids=taxes_ids,
        )
        res["activity_id"] = self.activity_id.id
        return res
