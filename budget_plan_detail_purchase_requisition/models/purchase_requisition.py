# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, fields, models


class PurchaseRequisitionLine(models.Model):
    _name = "purchase.requisition.line"
    _inherit = [
        "analytic.dimension.line",
        "budget.docline.mixin.base",
        "purchase.requisition.line",
    ]
    _analytic_tag_field_name = "analytic_tag_ids"

    analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        string="Analytic Tags",
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
        res["fund_id"] = self.fund_id.id
        res["analytic_tag_ids"] = [Command.set(self.analytic_tag_ids.ids)]
        return res

    def _convert_analytics(self, analytic_distribution=False):
        Analytic = self.env["account.analytic.account"]
        analytics = analytic_distribution or self[self._budget_analytic_field]
        if not analytics:
            return Analytic
        # Check analytic from distribution it send data with JSON type 'dict'
        # and we need convert it to analytic object
        if self._budget_analytic_field == "analytic_distribution":
            account_analytic_ids = [
                int(v) for k in analytics.keys() for v in k.split(",")
            ]
            analytics = Analytic.browse(account_analytic_ids)
        return analytics
