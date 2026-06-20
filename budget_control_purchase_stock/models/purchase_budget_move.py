# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class PurchaseBudgetMove(models.Model):
    _inherit = "purchase.budget.move"

    stock_picking_id = fields.Many2one(
        comodel_name="stock.picking",
        readonly=True,
        index=True,
        ondelete="set null",
        help="When set, this uncommit was triggered by a delivery order lot tracing.",
    )

    @api.depends("purchase_id", "stock_picking_id")
    def _compute_source_document(self):
        res = super()._compute_source_document()
        for rec in self.filtered("stock_picking_id"):
            if not rec.source_document:
                rec.source_document = rec.stock_picking_id.name
        return res
