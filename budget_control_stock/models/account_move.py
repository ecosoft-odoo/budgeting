# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model_create_multi
    def create(self, vals_list):
        """Flag SVL JEs without a stock budget source as not_affect_budget."""
        moves = super().create(vals_list)
        moves._compute_not_affect_budget_for_svl()
        return moves

    def write(self, vals):
        """Recompute stock commit when JE state changes.

        recompute_budget_move handles both re-commit and uncommit
        (via _recommit_via_valuation_lines) in one pass.
        For multi-step deliveries, recompute the upstream PICK move that owns
        the commitment even though the valuation entry belongs to the OUT move.
        """
        res = super().write(vals)
        if vals.get("state") in ("draft", "posted", "cancel"):
            stock_moves = self.mapped("stock_valuation_layer_ids.stock_move_id")
            stock_moves._get_budget_commit_source_moves().recompute_budget_move()
            self._compute_not_affect_budget_for_svl()
        return res

    def _compute_not_affect_budget_for_svl(self):
        """Flag an SVL JE only when its move chain has no budget source."""
        for move in self:
            if move.move_type != "entry":
                continue
            stock_move = move.stock_move_id
            not_affect = bool(
                stock_move and not stock_move._should_valuation_affect_budget()
            )
            if move.not_affect_budget != not_affect:
                move.not_affect_budget = not_affect
                if not not_affect and move.state == "posted":
                    move.recompute_budget_move()
