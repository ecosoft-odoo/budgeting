# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class HRExpense(models.Model):
    _name = "hr.expense"
    _inherit = ["hr.expense", "budget.docline.mixin"]
    _doc_date_fields = ["sheet_id.write_date"]

    budget_move_ids = fields.One2many(
        comodel_name="expense.budget.move",
        inverse_name="expense_id",
    )

    def recompute_budget_move(self):
        self.mapped("budget_move_ids").unlink()
        self.commit_budget()
        move_lines = self.env["account.move.line"].search(
            [("expense_id", "in", self.ids)]
        )
        move_lines.uncommit_expense_budget()

    def _check_amount_currency_tax(self, date, doc_type="expense"):
        self.ensure_one()
        budget_period = self.env["budget.period"]._get_eligible_budget_period(
            date, doc_type=doc_type
        )
        amount_currency = (
            budget_period.include_tax
            and self.total_amount
            or self.untaxed_amount
        )
        return amount_currency

    def commit_budget(self, reverse=False, move_line_id=False):
        """Create budget commit for each expense."""
        for expense in self:
            if expense.can_commit() and expense.state in ("approved", "done"):
                account = expense.account_id
                analytic_account = expense.analytic_account_id
                amount_currency = expense._check_amount_currency_tax(
                    self.date_commit
                )
                currency = expense.currency_id
                vals = expense._prepare_budget_commitment(
                    account,
                    analytic_account,
                    self.date_commit,
                    amount_currency,
                    currency,
                    reverse=reverse,
                )
                # Document specific vals
                vals.update(
                    {
                        "expense_id": expense.id,
                        "analytic_tag_ids": [
                            (6, 0, expense.analytic_tag_ids.ids)
                        ],
                        "move_line_id": move_line_id,
                    }
                )
                budget_move = self.env["expense.budget.move"].create(vals)
                if reverse:  # On reverse, make sure not over returned
                    self.env["budget.period"].check_over_returned_budget(
                        self.sheet_id
                    )
                return budget_move
            else:
                expense.budget_move_ids.unlink()

    # def uncommit_expense_budget(self):
    #     """For vendor bill in valid state, do uncommit for related expense."""
    #     for expense in self:
    #         if expense.sheet_id.state in ('post', 'done') and \
    #                 expense.state in ('approved', 'done'):
    #             expense.commit_budget(reverse=True, move_line_id=)
