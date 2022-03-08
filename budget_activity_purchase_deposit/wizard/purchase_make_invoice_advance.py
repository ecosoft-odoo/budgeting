# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class PurchaseAdvancePaymentInv(models.TransientModel):
    _inherit = "purchase.advance.payment.inv"

    activity_id = fields.Many2one(
        comodel_name="budget.activity",
        string="Activity",
        index=True,
    )

    def _get_purchase_order(self):
        """ Get purchase order """
        order = False
        active_id = self._context.get("active_id")
        active_model = self._context.get("active_model")
        if active_model == "purchase.order":
            order = self.env[active_model].browse(active_id)
        return order

    @api.model
    def default_get(self, field_list):
        """ Default activity """
        res = super().default_get(field_list)
        order = self._get_purchase_order()
        if order:
            order_line = order.order_line
            if len(order_line.filtered(lambda l: l.activity_id)) == 1:
                res.update({"activity_id": order_line.activity_id.id})
        return res

    def _prepare_advance_purchase_line(self, order, product, tax_ids, amount):
        res = super()._prepare_advance_purchase_line(
            order, product, tax_ids, amount
        )
        res.update({"activity_id": self.activity_id.id})
        return res

    def _prepare_deposit_val(self, order, po_line, amount):
        res = super()._prepare_deposit_val(order, po_line, amount)
        res["invoice_line_ids"][0][2].update(
            {
                "activity_id": po_line.activity_id.id,
            }
        )
        return res
