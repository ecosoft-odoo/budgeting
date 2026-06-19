# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountBudgetMove(models.Model):
    _inherit = "account.budget.move"

    @api.depends("move_id")
    def _compute_source_document(self):
        res = super()._compute_source_document()
        for rec in self.filtered(lambda r: r.move_line_id.stock_valuation_layer_ids):
            if rec.source_document:
                continue
            stock_moves = rec.move_line_id.stock_valuation_layer_ids.mapped(
                "stock_move_id"
            )
            if stock_moves and stock_moves[0].picking_id:
                rec.source_document = stock_moves[0].picking_id.display_name
        return res
