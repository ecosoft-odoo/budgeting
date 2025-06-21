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
