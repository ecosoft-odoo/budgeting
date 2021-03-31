# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class HRExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    budget_move_ids = fields.One2many(
        comodel_name="expense.budget.move",
        inverse_name="sheet_id",
    )

    def recompute_budget_move(self):
        self.mapped("expense_line_ids").recompute_budget_move()

    def write(self, vals):
        """
        - UnCommit budget when state post
        - Cancel/Draft document should delete all budget commitment
        """
        res = super().write(vals)
        if vals.get("state") in ("approve", "cancel", "draft"):
            for expense in self.mapped("expense_line_ids"):
                expense.commit_budget()
        return res

    def approve_expense_sheets(self):
        res = super().approve_expense_sheets()
        self.flush()
        BudgetPeriod = self.env["budget.period"]
        for doc in self:
            BudgetPeriod.check_budget(doc.expense_line_ids, doc_type="expense")
        return res

    def action_submit_sheet(self):
        res = super().action_submit_sheet()
        self.flush()
        BudgetPeriod = self.env["budget.period"]
        for doc in self:
            BudgetPeriod.check_budget_precommit(
                doc.expense_line_ids, doc_type="expense"
            )
        return res


class HRExpense(models.Model):
    _name = "hr.expense"
    _inherit = ["hr.expense", "budget.docline.mixin"]
    _budget_date_commit_fields = ["sheet_id.write_date"]

    budget_move_ids = fields.One2many(
        comodel_name="expense.budget.move",
        inverse_name="expense_id",
    )

    def _budget_model(self):
        return (
            self.env.context.get("alt_budget_move_model")
            or "expense.budget.move"
        )

    def _budget_field(self):
        return (
            self.env.context.get("alt_budget_move_field") or "budget_move_ids"
        )

    def recompute_budget_move(self):
        MoveLine = self.env["account.move.line"]
        for expense in self:
            expense[self._budget_field()].unlink()
            expense.commit_budget()
            move_lines = MoveLine.search([("expense_id", "in", expense.ids)])
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

    def commit_budget(self, reverse=False, **kwargs):
        """Create budget commit for each expense."""
        self.prepare_commit()
        to_commit = self.env.context.get("force_commit") or self.state in (
            "approved",
            "done",
        )
        if self.can_commit and to_commit:
            account = self.account_id
            analytic_account = self.analytic_account_id
            amount_currency = self._check_amount_currency_tax(self.date_commit)
            currency = self.currency_id
            vals = self._prepare_budget_commitment(
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
                    "expense_id": self.id,
                    "analytic_tag_ids": [(6, 0, self.analytic_tag_ids.ids)],
                }
            )
            # Assign kwargs where value is not False
            vals.update({k: v for k, v in kwargs.items() if v})
            # Create budget move
            budget_move = self.env[self._budget_model()].create(vals)
            if reverse:  # On reverse, make sure not over returned
                self.env["budget.period"].check_over_returned_budget(
                    self.sheet_id
                )
            return budget_move
        else:
            self[self._budget_field()].unlink()
