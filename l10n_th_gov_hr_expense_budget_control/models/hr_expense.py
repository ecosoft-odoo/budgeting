# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class HRExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def write(self, vals):
        """Uncommit budget for source purchase request document."""
        res = super().write(vals)
        if vals.get("state"):
            self.mapped("purchase_request_id").recompute_budget_move()
        return res


class HRExpense(models.Model):
    _inherit = "hr.expense"

    def uncommit_purchase_request_budget(self):
        """For expense in valid state, do uncommit for related PR."""
        budget_moves = self.env["purchase.request.budget.move"]
        for ex in self:
            ex_state = ex.sheet_id.state
            if ex_state in ("approve", "post", "done") or self.env.context.get(
                "force_commit"
            ):
                for pr_line in ex.pr_line_id.filtered("amount_commit"):
                    budget_moves = pr_line.commit_budget(
                        reverse=True,
                        expense_id=ex.id,
                        date=ex.date_commit,
                    )
                    budget_moves |= budget_moves
            else:  # Cancel, Submit or draft, not commitment line
                self.env["purchase.request.budget.move"].search(
                    [("expense_id", "=", ex.id)]
                ).unlink()
        return budget_moves
