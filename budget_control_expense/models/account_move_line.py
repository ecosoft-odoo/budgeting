# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.tools import float_compare


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _init_docline_budget_vals(self, budget_vals, analytic_id):
        self.ensure_one()
        res = super()._init_docline_budget_vals(budget_vals, analytic_id)
        expense = self.expense_id
        if expense:
            percent_analytic = self[self._budget_analytic_field].get(str(analytic_id))
            total_untax_amount = expense.total_amount - expense.tax_amount
            # Amount from expense is tax included, need to convert to amount_untaxed
            budget_vals["amount_currency"] = total_untax_amount * (
                percent_analytic / 100
            )
        return res

    def _condition_skip_uncommit_expense(self, move):
        return move.move_type != "in_invoice" or not move.expense_sheet_id

    def uncommit_expense_budget(self):
        """Uncommit the budget for related expenses
        when the vendor bill is in a valid state."""
        Expense = self.env["hr.expense"]
        AnalyticAccount = self.env["account.analytic.account"]

        lines = self.filtered(lambda line: not line.not_affect_budget)
        reverse_entries = []
        draft_line_ids = []
        for ml in lines:
            move = ml.move_id
            # Expense created journal entry with vendor bill or not expense
            if self._condition_skip_uncommit_expense(move):
                continue

            if move.state == "posted":
                expense = ml.expense_id.filtered("amount_commit")
                # Because this is not invoice, we need to compare account
                if not expense:
                    continue
                # Also test for future advance extension, never uncommit for advance
                if hasattr(expense, "advance") and expense["advance"]:
                    continue

                if ml.analytic_distribution:
                    analytic_accounts = {
                        int(aid): AnalyticAccount.browse(int(aid))
                        for aid in ml.analytic_distribution
                    }
                    for analytic_id, _ in ml.analytic_distribution.items():
                        # Base expense commitments already exist here, so
                        # prepare_commit has the same outcome as commit_budget
                        # without issuing one CREATE per journal line.
                        expense.prepare_commit()
                        if not expense.can_commit or not (
                            self.env.context.get("force_commit")
                            or expense._valid_commit_state()
                        ):
                            continue
                        commit_kwargs = {
                            "move_line_id": ml.id,
                            "date": ml.date_commit,
                            "analytic_account_id": analytic_accounts[int(analytic_id)],
                        }
                        reverse_entries.append(
                            (
                                expense,
                                commit_kwargs,
                                expense._prepare_commit_vals(
                                    reverse=True, **commit_kwargs
                                ),
                            )
                        )
            else:  # Cancel or draft, not commitment line
                draft_line_ids.append(ml.id)

        # A normal posted expense cannot over-return, so all reversals can be
        # created together.  Preserve the exact legacy adjustment order for an
        # exceptional document whose projected credit would exceed its debit.
        batch_vals = []
        entries_by_sheet = {}
        for entry in reverse_entries:
            entries_by_sheet.setdefault(entry[0].sheet_id.id, []).append(entry)
        for entries in entries_by_sheet.values():
            sheet = entries[0][0].sheet_id
            existing_moves = sheet.budget_move_ids
            projected_debit = sum(existing_moves.mapped("debit")) + sum(
                vals["debit"] for entry in entries for vals in entry[2]
            )
            projected_credit = sum(existing_moves.mapped("credit")) + sum(
                vals["credit"] for entry in entries for vals in entry[2]
            )
            if float_compare(projected_credit, projected_debit, 2) == 1:
                for expense, commit_kwargs, _vals in entries:
                    expense.commit_budget(reverse=True, **commit_kwargs)
            else:
                batch_vals.extend(vals for entry in entries for vals in entry[2])

        if batch_vals:
            budget_moves = self.env[Expense._budget_model()].create(batch_vals)
            Expense._update_template_line_batch(budget_moves)
        if draft_line_ids:
            self.env[Expense._budget_model()].search(
                [("move_line_id", "in", draft_line_ids)]
            ).unlink()
