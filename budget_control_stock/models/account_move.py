# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def write(self, vals):
        """Recompute stock commit when JE state changes.

        recompute_budget_move handles both re-commit and uncommit
        (via _recommit_via_valuation_lines) in one pass.
        Only recompute for moves belonging to picking types with budget_commit enabled.
        """
        res = super().write(vals)
        if vals.get("state") in ("draft", "posted", "cancel"):
            stock_moves = self.mapped("stock_valuation_layer_ids.stock_move_id")
            stock_moves = stock_moves.filtered(
                lambda m: m.picking_id.picking_type_id.budget_commit
            )
            stock_moves.recompute_budget_move()
        return res
