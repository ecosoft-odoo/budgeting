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
            # Amount from expense is tax included, need to convert to amount_untaxed
            base_lines = [
                expense._convert_to_tax_base_line_dict(
                    price_unit=expense.unit_amount, quantity=expense.quantity
                )
            ]
            taxes_totals = self.env["account.tax"]._compute_taxes(base_lines)["totals"][
                expense.currency_id
            ]
            total_amount = taxes_totals["amount_untaxed"]
            budget_vals["amount_currency"] = total_amount
        return res

    def uncommit_expense_budget(self):
        """Uncommit the budget for related expenses when the vendor bill is in a valid state."""
        Expense = self.env["hr.expense"]
        for ml in self:
            inv_state = ml.move_id.state
            # Skip if not expense or tax line
            if not ml.move_id.expense_sheet_id or ml.display_type == "tax":
                continue
            if inv_state == "posted":
                expense = ml.expense_id.filtered("amount_commit")
                # Because this is not invoice, we need to compare account
                if not expense:
                    continue
                # Also test for future advance extension, never uncommit for advance
                if hasattr(expense, "advance") and expense["advance"]:
                    continue
                expense.commit_budget(
                    reverse=True,
                    move_line_id=ml.id,
                    date=ml.date_commit,
                    analytic_distribution=expense.fwd_analytic_distribution or False,
                )
            else:  # Cancel or draft, not commitment line
                self.env[Expense._budget_model()].search(
                    [("move_line_id", "=", ml.id)]
                ).unlink()
