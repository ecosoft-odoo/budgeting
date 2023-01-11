# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class PurchaseRequisitionLine(models.Model):
    _name = "purchase.requisition.line"
    _inherit = ["purchase.requisition.line", "budget.docline.mixin.base"]
    _budget_analytic_field = "account_analytic_id"

    def _prepare_purchase_order_line(
        self, name, product_qty=0.0, price_unit=0.0, taxes_ids=False
    ):
        self.ensure_one()
        po_line_vals = super()._prepare_purchase_order_line(
            name, product_qty, price_unit, taxes_ids
        )
        # NOTE: Not test with multi pr lines
        if self.purchase_request_lines.fwd_analytic_account_id:
            po_line_vals[
                "account_analytic_id"
            ] = self.purchase_request_lines.fwd_analytic_account_id.id
        return po_line_vals
