# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def write(self, vals):
        """Uncommit budget for source purchase request document."""
        res = super().write(vals)
        if vals.get("state") in ("purchase", "cancel"):
            self.mapped("order_line.purchase_request_lines").recompute_budget_move()
        return res


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def uncommit_purchase_request_budget(self):
        """For purchase in valid state, do uncommit for related PR.

        Batched to avoid one create / search-unlink per purchase line, while
        keeping the result identical to the former per-line loop. For each
        purchase line, that loop did:

            if force_commit or po_state in ("purchase", "done"):
                for pr_line in po_line.purchase_request_lines.filtered("amount_commit"):
                    pr_line.commit_budget(
                        reverse=True,
                        analytic_account_id=pr_line.fwd_analytic_distribution or False,
                        purchase_line_id=po_line.id,
                        date=po_line.date_commit,
                    )
            else:  # cancel/draft
                search([("purchase_line_id", "=", po_line.id)]).unlink()

        So each (po_line, pr_line) pair produces its own reverse move (a PR
        line shared by several PO lines yields one reverse move per PO line),
        and cancel/draft purchase lines delete their reverse moves in one go.
        """
        BudgetMove = self.env["purchase.request.budget.move"]
        PRLine = self.env["purchase.request.line"]
        force_commit = self.env.context.get("force_commit")

        # cancel/draft purchase lines: delete all their reverse moves in one query
        unlink_po_lines = self.filtered(
            lambda line: not force_commit
            and line.order_id.state not in ("purchase", "done")
        )
        if unlink_po_lines:
            BudgetMove.search(
                [("purchase_line_id", "in", unlink_po_lines.ids)]
            ).unlink()

        # purchase/done purchase lines: build reverse commits for related PR lines
        commit_po_lines = self - unlink_po_lines
        if not commit_po_lines:
            return BudgetMove

        # Pairs in the same order the nested loop produced them: outer = po_line,
        # inner = pr_line (only those with amount_commit).
        pairs = []
        all_pr_line_ids = []
        seen_pr_line_ids = set()
        for po_line in commit_po_lines:
            for pr_line in po_line.purchase_request_lines.filtered("amount_commit"):
                pairs.append(
                    (
                        pr_line,
                        {
                            "analytic_account_id": (
                                pr_line.fwd_analytic_distribution or False
                            ),
                            "purchase_line_id": po_line.id,
                            "date": po_line.date_commit,
                        },
                    )
                )
                if pr_line.id not in seen_pr_line_ids:
                    seen_pr_line_ids.add(pr_line.id)
                    all_pr_line_ids.append(pr_line.id)
        if not pairs:
            return BudgetMove
        all_pr_lines = PRLine.browse(all_pr_line_ids)

        # Keep the same required-analytic validation as commit_budget().
        for pr_line in all_pr_lines:
            if pr_line._check_required_analytic():
                raise UserError(self.env._("Please fill analytic account."))

        # Set date_commit once for all eligible PR lines (prepare_commit path).
        all_pr_lines.prepare_commit_batch()

        # commit_budget() only creates a reverse move when can_commit AND a valid
        # commit state; otherwise it deletes the line's existing moves. Mirror
        # that here so the result matches the per-line calls.
        to_commit = all_pr_lines.filtered(
            lambda line: line.can_commit
            and (force_commit or line._valid_commit_state())
        )
        no_commit = all_pr_lines - to_commit
        if no_commit:
            no_commit.mapped(no_commit._budget_field()).unlink()

        if not to_commit:
            return BudgetMove

        # Build the reverse commit vals for every (pr_line, po_line) pair, in the
        # same order as the original nested loop, then create them in one batch.
        budget_vals = []
        to_commit_ids = set(to_commit.ids)
        for pr_line, vals in pairs:
            if pr_line.id not in to_commit_ids:
                continue
            budget_vals.extend(pr_line._prepare_commit_vals(reverse=True, **vals))
        if not budget_vals:
            return BudgetMove

        budget_moves = BudgetMove.create(budget_vals)
        # Template/KPI assignment is batched (grouped by period + control key)
        # instead of one resolution per move. The former commit_budget() path
        # resolved the period from the source PR date, not the reverse move's
        # PO date, so preserve that behavior explicitly.
        period_dates = {
            move.id: move.purchase_request_line_id.date_commit for move in budget_moves
        }
        to_commit._update_template_line_batch(budget_moves, period_dates=period_dates)
        # On reverse, ensure no over-return. Per-line like commit_budget(), as it
        # may create an additional adjustment move based on the line's totals.
        BudgetPeriod = self.env["budget.period"]
        for pr_line in to_commit:
            BudgetPeriod.check_over_returned_budget(pr_line)
        return budget_moves
