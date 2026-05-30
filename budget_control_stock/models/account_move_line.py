# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _condition_skip_uncommit_stock(self, move):
        """Skip if this account move line is not related to a stock valuation."""
        return not move.stock_valuation_layer_ids

    def _get_lot_uncommit_context(self, move):
        """Return context for lot-based uncommit.

        Each stock valuation JE links to exactly one SVL (one per serial/lot).
        Always scope the uncommit to the per-SVL qty so cancelling one JE
        restores only that lot's commitment, not the full move qty.
        For lot_price source, also override the unit price from the lot.
        """
        svls = move.stock_valuation_layer_ids
        if not svls:
            return {}
        svl = svls[0]
        if not svl.lot_id:
            return {}
        stock_move = svl.stock_move_id
        ctx = {"product_qty": abs(svl.quantity)}
        if stock_move.picking_id.picking_type_id.budget_price_source == "lot_price":
            ctx["budget_lot_price"] = svl.lot_id.standard_price
        return ctx

    def uncommit_stock_budget(self):
        """Uncommit the budget for related stock moves
        when the stock valuation entry is in a valid state."""
        AnalyticAccount = self.env["account.analytic.account"]

        for ml in self:
            move = ml.move_id
            # Not related to stock valuation
            if self._condition_skip_uncommit_stock(move):
                continue

            # Get the stock.move from the valuation layer
            stock_moves = move.stock_valuation_layer_ids.mapped("stock_move_id")
            if not stock_moves:
                continue

            if move.state == "posted":
                stock_moves = stock_moves.filtered(
                    lambda m: m.amount_commit
                    and any(v > 0 for v in m.amount_commit.values())
                )
                if not stock_moves:
                    # 2-step delivery: SVL is on OUT move (no budget_commit),
                    # but the commit is on the upstream PICK move.
                    svl_moves = move.stock_valuation_layer_ids.mapped("stock_move_id")
                    stock_moves = svl_moves.mapped("move_orig_ids").filtered(
                        lambda m: m.amount_commit
                        and any(v > 0 for v in m.amount_commit.values())
                    )
                if not stock_moves:
                    continue

                if ml.analytic_distribution:
                    analytic_accounts = {
                        int(aid): AnalyticAccount.browse(int(aid))
                        for aid in ml.analytic_distribution
                    }
                    lot_ctx = self._get_lot_uncommit_context(move)
                    for analytic_id, _ in ml.analytic_distribution.items():
                        for stock_move in stock_moves:
                            stock_move.with_context(**lot_ctx).commit_budget(
                                reverse=True,
                                account_move_line_id=ml.id,
                                date=ml.date_commit,
                                analytic_account_id=analytic_accounts[int(analytic_id)],
                            )
            else:  # Cancel or draft, not commitment line
                StockMove = self.env["stock.move"]
                self.env[StockMove._budget_model()].search(
                    [("account_move_line_id", "=", ml.id)]
                ).unlink()

    def _check_required_analytic(self):
        if self.move_id.stock_valuation_layer_ids:
            return False
        return super()._check_required_analytic()
