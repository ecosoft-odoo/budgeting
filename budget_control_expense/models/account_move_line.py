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

    def _prepare_expense_reverse_entries(self):
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
                    # Do the state/date preparation once per journal line.  The
                    # former commit_budget() loop repeated this for every analytic.
                    expense.prepare_commit()
                    if not expense.can_commit or not (
                        self.env.context.get("force_commit")
                        or expense._valid_commit_state()
                    ):
                        continue
                    analytic_accounts = {
                        int(aid): AnalyticAccount.browse(int(aid))
                        for aid in ml.analytic_distribution
                    }
                    for analytic_id, _ in ml.analytic_distribution.items():
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
        return reverse_entries, draft_line_ids

    def _create_expense_reverse_entries_batch(self, reverse_entries):
        # A normal posted expense cannot over-return, so all reversals can be
        # created together.  Preserve the exact legacy adjustment order for an
        # exceptional document whose balance exceeds at any intermediate step.
        # Checking every prefix (not only the final total) also covers mixed
        # positive/negative expense lines.
        batch_vals = []
        batch_period_dates = []
        entries_by_sheet = {}
        for entry in reverse_entries:
            entries_by_sheet.setdefault(entry[0].sheet_id.id, []).append(entry)
        for entries in entries_by_sheet.values():
            sheet = entries[0][0].sheet_id
            existing_moves = sheet.budget_move_ids
            projected_debit = sum(existing_moves.mapped("debit"))
            projected_credit = sum(existing_moves.mapped("credit"))
            use_legacy_order = False
            for _expense, _commit_kwargs, vals_list in entries:
                projected_debit += sum(vals["debit"] for vals in vals_list)
                projected_credit += sum(vals["credit"] for vals in vals_list)
                if float_compare(projected_credit, projected_debit, 2) == 1:
                    use_legacy_order = True
                    break
            if use_legacy_order:
                for expense, commit_kwargs, _vals in entries:
                    expense.commit_budget(reverse=True, **commit_kwargs)
            else:
                for expense, _commit_kwargs, vals_list in entries:
                    batch_vals.extend(vals_list)
                    # Legacy _update_template_line() resolves the period from
                    # the source expense date, which can differ from the JE date.
                    batch_period_dates.extend([expense.date_commit] * len(vals_list))

        if batch_vals:
            Expense = self.env["hr.expense"]
            budget_moves = self.env[Expense._budget_model()].create(batch_vals)
            period_dates = dict(zip(budget_moves.ids, batch_period_dates, strict=False))
            Expense._update_template_line_batch(budget_moves, period_dates=period_dates)

    def uncommit_expense_budget(self):
        """Uncommit the budget for related expenses
        when the vendor bill is in a valid state."""
        Expense = self.env["hr.expense"]
        reverse_entries, draft_line_ids = self._prepare_expense_reverse_entries()
        self._create_expense_reverse_entries_batch(reverse_entries)
        if draft_line_ids:
            self.env[Expense._budget_model()].search(
                [("move_line_id", "in", draft_line_ids)]
            ).unlink()
