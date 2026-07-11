# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model_create_multi
    def create(self, vals_list):
        """Flag SVL JEs of non-commit picking types as not_affect_budget."""
        moves = super().create(vals_list)
        moves._compute_not_affect_budget_for_svl()
        return moves

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
            self._compute_not_affect_budget_for_svl()
        return res

    def _compute_not_affect_budget_for_svl(self):
        """Flag SVL JE of a picking type without budget_commit as not_affect_budget."""
        for move in self:
            if move.move_type != "entry":
                continue
            stock_move = move.stock_move_id
            # A picking type that does not commit budget (e.g. receipts) should
            # not record actual via its valuation JE either, mirroring the rule
            # already applied to stock.move (see StockMove._compute_can_commit).
            not_affect = bool(
                stock_move and not stock_move.picking_id.picking_type_id.budget_commit
            )
            if move.not_affect_budget != not_affect:
                move.not_affect_budget = not_affect
