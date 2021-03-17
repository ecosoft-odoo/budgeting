# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class HRExpense(models.Model):
    _name = "hr.expense"
    _inherit = ["hr.expense", "budget.docline.mixin"]

    budget_move_ids = fields.One2many(
        comodel_name="expense.budget.move",
        inverse_name="expense_id",
    )

    def recompute_budget_move(self):
        self.mapped("budget_move_ids").unlink()
        self.commit_budget()
        self.uncommit_expense_budget()

    def _budget_move_create(self, vals):
        self.ensure_one()
        budget_move = self.env["expense.budget.move"].create(vals)
        return budget_move

    def _budget_move_unlink(self):
        self.ensure_one()
        self.budget_move_ids.unlink()

    def _check_amount_currency_tax(self, date, doc_type="expense"):
        self.ensure_one()
        budget_period = self.env["budget.period"]._get_eligible_budget_period(
            date, doc_type
        )
        amount_currency = (
            budget_period.include_tax
            and self.total_amount
            or self.untaxed_amount
        )
        return amount_currency

    def commit_budget(self, reverse=False):
        """Create budget commit for each expense."""
        doc_model = self.env["hr.expense"]
        for expense in self:
            if expense.state in ("approved", "done"):
                if not self.filtered_domain(
                    self._budget_domain
                ):  # With correct dom
                    return
                account = expense.account_id
                analytic_account = expense.analytic_account_id
                doc_date = expense.date
                amount_currency = expense._check_amount_currency_tax(doc_date)
                currency = expense.currency_id
                vals = expense._prepare_budget_commitment(
                    account,
                    analytic_account,
                    doc_date,
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
                    }
                )
                budget_move = expense._budget_move_create(vals)
                if reverse and not expense._context.get(
                    "force_check_reverse", False
                ):  # On reverse, make sure not over returned
                    self.env["budget.period"].check_over_returned_budget(
                        self.sheet_id
                    )
                doc_model |= budget_move
            else:
                expense._budget_move_unlink()
            return doc_model

    def _search_domain_expense(self):
        domain = self.sheet_id.state in ("post", "done") and self.state in (
            "approved",
            "done",
        )
        return domain

    def uncommit_expense_budget(self):
        """For vendor bill in valid state, do uncommit for related expense."""
        for expense in self:
            domain = expense._search_domain_expense()
            if domain:
                expense.commit_budget(reverse=True)
