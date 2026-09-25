# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PurchaseRequisitionLine(models.Model):
    _name = "purchase.requisition.line"
    _inherit = ["purchase.requisition.line", "budget.docline.mixin.base"]
    _budget_analytic_field = "account_analytic_id"

    date_commit = fields.Date(
        copy=False,
        readonly=True,
    )

    def _prepare_purchase_order_line(
        self, name, product_qty=0.0, price_unit=0.0, taxes_ids=False
    ):
        res = super()._prepare_purchase_order_line(
            name,
            product_qty=product_qty,
            price_unit=price_unit,
            taxes_ids=taxes_ids,
        )
        # Check if date_commit is not in the fiscal year, then update it
        fy_dates = self.company_id.compute_fiscalyear_dates(
            fields.Date.context_today(self)
        )
        if self.date_commit and self.date_commit > fy_dates["date_to"]:
            res["date_commit"] = self.date_commit
        return res
