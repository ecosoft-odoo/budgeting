# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


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

        for ml in self:
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
                        expense.commit_budget(
                            reverse=True,
                            move_line_id=ml.id,
                            date=ml.date_commit,
                            analytic_account_id=analytic_accounts[int(analytic_id)],
                        )
            else:  # Cancel or draft, not commitment line
                self.env[Expense._budget_model()].search(
                    [("move_line_id", "=", ml.id)]
                ).unlink()
