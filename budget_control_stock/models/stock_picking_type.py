# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    budget_commit = fields.Boolean(
        string="Commit Budget",
        default=False,
        help="When enabled, stock moves of this operation type will commit budget.",
    )
    budget_price_source = fields.Selection(
        selection=[
            ("standard_price", "Product Standard Price"),
            ("lot_price", "Lot Standard Price"),
        ],
        default="standard_price",
        help="Source of unit price for budget commitment.\n"
        "- Product Standard Price: use product.standard_price (default).\n"
        "- Lot Standard Price: use lot.standard_price per reserved lot (for FIFO).",
    )
