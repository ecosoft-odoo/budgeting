# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class PurchaseRequisitionLine(models.Model):
    _inherit = "purchase.requisition.line"

    def _prepare_purchase_order_line(
        self, name, product_qty=0.0, price_unit=0.0, taxes_ids=False
    ):
        self.ensure_one()
        res = super()._prepare_purchase_order_line(
            name,
            product_qty=product_qty,
            price_unit=price_unit,
            taxes_ids=taxes_ids,
        )
        res["job_order_id"] = self.job_order_id.id
        return res
