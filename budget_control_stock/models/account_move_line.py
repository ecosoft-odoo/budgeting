# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.exceptions import UserError


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

    def _resolve_stock_moves_for_uncommit(self, move):
        """Return the stock.move(s) to reverse-commit for a posted valuation JE.

        For 2-step delivery the SVL sits on the OUT move (no budget_commit),
        so follow ``move_orig_ids`` to the upstream PICK move that holds the
        commitment.
        """
        stock_moves = move.stock_valuation_layer_ids.mapped("stock_move_id")
        if not stock_moves:
            return self.env["stock.move"]
        stock_moves = stock_moves.filtered(
            lambda m: m.amount_commit and any(v > 0 for v in m.amount_commit.values())
        )
        if stock_moves:
            return stock_moves
        # 2-step delivery: SVL is on OUT move (no budget_commit),
        # but the commit is on the upstream PICK move.
        svl_moves = move.stock_valuation_layer_ids.mapped("stock_move_id")
        return svl_moves.mapped("move_orig_ids").filtered(
            lambda m: m.amount_commit and any(v > 0 for v in m.amount_commit.values())
        )

    def _split_stock_uncommit_lines(self):
        relevant_mls = self.filtered(
            lambda ml: not ml._condition_skip_uncommit_stock(ml.move_id)
        )
        posted_mls = relevant_mls.filtered(lambda ml: ml.move_id.state == "posted")
        return posted_mls, relevant_mls - posted_mls

    def _prepare_stock_uncommit_pairs(self, posted_mls):
        """Return ordered (stock move, vals, context) pairs and unique moves."""
        AnalyticAccount = self.env["account.analytic.account"]
        pairs = []
        all_stock_move_ids = []
        seen_stock_move_ids = set()
        for ml in posted_mls.filtered("analytic_distribution"):
            stock_moves = self._resolve_stock_moves_for_uncommit(ml.move_id)
            if not stock_moves:
                continue
            analytic_accounts = {
                int(aid): AnalyticAccount.browse(int(aid))
                for aid in ml.analytic_distribution
            }
            lot_ctx = self._get_lot_uncommit_context(ml.move_id)
            for analytic_id in ml.analytic_distribution:
                for stock_move in stock_moves:
                    pairs.append(
                        (
                            stock_move,
                            {
                                "account_move_line_id": ml.id,
                                "date": ml.date_commit,
                                "analytic_account_id": analytic_accounts[
                                    int(analytic_id)
                                ],
                            },
                            lot_ctx,
                        )
                    )
                    if stock_move.id not in seen_stock_move_ids:
                        seen_stock_move_ids.add(stock_move.id)
                        all_stock_move_ids.append(stock_move.id)
        return pairs, self.env["stock.move"].browse(all_stock_move_ids)

    def _prepare_stock_uncommit_vals(self, pairs, to_commit):
        """Build reverse values while preserving the former period lookup date."""
        budget_vals = []
        move_period_dates = []
        to_commit_ids = set(to_commit.ids)
        for stock_move, vals, lot_ctx in pairs:
            if stock_move.id not in to_commit_ids:
                continue
            line_vals = stock_move.with_context(**lot_ctx)._prepare_commit_vals(
                reverse=True, **vals
            )
            budget_vals.extend(line_vals)
            # commit_budget() formerly resolved the template from the source
            # stock move's date_commit, even when the reverse move used the JE date.
            move_period_dates.extend([stock_move.date_commit] * len(line_vals))
        return budget_vals, move_period_dates

    def uncommit_stock_budget(self):
        """Uncommit the budget for related stock moves
        when the stock valuation entry is in a valid state.

        Batched: cancel/draft lines delete their reverse moves in one query,
        posted lines build all reverse-commit vals and create them in one batch.
        """
        StockBudgetMove = self.env["stock.budget.move"]
        BudgetPeriod = self.env["budget.period"]

        if not self:
            return StockBudgetMove

        posted_mls, unlink_mls = self._split_stock_uncommit_lines()
        if unlink_mls:
            StockBudgetMove.search(
                [("account_move_line_id", "in", unlink_mls.ids)]
            ).unlink()

        if not posted_mls:
            return StockBudgetMove

        # One reverse move per (ml, analytic, stock_move) pair, in nested order.
        pairs, all_stock_moves = self._prepare_stock_uncommit_pairs(posted_mls)
        if not pairs:
            return StockBudgetMove

        for stock_move in all_stock_moves:
            if stock_move._check_required_analytic():
                raise UserError(self.env._("Please fill analytic account."))
        all_stock_moves.prepare_commit_batch()

        to_commit = all_stock_moves.filtered(
            lambda line: line.can_commit
            and (self.env.context.get("force_commit") or line._valid_commit_state())
        )
        no_commit = all_stock_moves - to_commit
        if no_commit:
            no_commit.mapped(no_commit._budget_field()).unlink()

        if not to_commit:
            return StockBudgetMove

        # Each pair runs in its own lot context so lot price/qty stay isolated.
        budget_vals, move_period_dates = self._prepare_stock_uncommit_vals(
            pairs, to_commit
        )
        if not budget_vals:
            return StockBudgetMove

        budget_moves = StockBudgetMove.create(budget_vals)
        period_dates = dict(zip(budget_moves.ids, move_period_dates, strict=False))
        to_commit._update_template_line_batch(budget_moves, period_dates=period_dates)
        # Per-record: may create an extra over-return adjustment move.
        for stock_move in to_commit:
            BudgetPeriod.check_over_returned_budget(stock_move)
        return budget_moves

    def _uncommit_stock_budget_sequential(self):
        """Former per-record uncommit, kept for parity tests only."""
        AnalyticAccount = self.env["account.analytic.account"]
        for ml in self:
            move = ml.move_id
            if self._condition_skip_uncommit_stock(move):
                continue
            stock_moves = move.stock_valuation_layer_ids.mapped("stock_move_id")
            if not stock_moves:
                continue
            if move.state == "posted":
                stock_moves = self._resolve_stock_moves_for_uncommit(move)
                if not stock_moves:
                    continue
                if ml.analytic_distribution:
                    analytic_accounts = {
                        int(aid): AnalyticAccount.browse(int(aid))
                        for aid in ml.analytic_distribution
                    }
                    lot_ctx = self._get_lot_uncommit_context(move)
                    for analytic_id in ml.analytic_distribution:
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
