# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HRExpense(models.Model):
    _name = "hr.expense"
    _inherit = ["hr.expense", "budget.docline.mixin"]
    _budget_date_commit_fields = ["sheet_id.write_date"]
    _budget_move_model = "expense.budget.move"
    _doc_rel = "sheet_id"

    budget_move_ids = fields.One2many(
        comodel_name="expense.budget.move",
        inverse_name="expense_id",
    )

    def _recompute_budget_move_sequential(self):
        """Keep the legacy order for carry-forward, whose checks are sheet-wide."""
        budget_field = self._budget_field()
        force_date_commit = self.env.context.get("force_date_commit", False)
        for expense in self:
            ex_date_commit = force_date_commit or expense.date_commit
            expense[budget_field].unlink()
            expense.with_context(force_date_commit=ex_date_commit).commit_budget()
            expense.forward_commit()

    def recompute_budget_move(self):
        forwarded = self.filtered(
            lambda expense: expense.fwd_analytic_distribution or expense.fwd_date_commit
        )
        if forwarded:
            # forward_commit() can create an over-return adjustment based on all
            # moves of the sheet.  Recreate the whole recordset sequentially when
            # any line is forwarded so intermediate balances stay identical.
            self._recompute_budget_move_sequential()
        else:
            # Normal expenses are independent and can safely share one
            # unlink/create/template update operation.
            self.recompute_budget_move_batch()
        self.mapped(
            "sheet_id.account_move_ids.invoice_line_ids"
        ).uncommit_expense_budget()

    def _can_batch_budget_precommit(self):
        # Advance lines override commit_budget() to use advance.budget.move;
        # the generic batch helper uses one model for the whole recordset.
        return not ("advance" in self._fields and any(self.mapped("advance")))

    def _init_docline_budget_vals(self, budget_vals, analytic_id):
        self.ensure_one()
        if not budget_vals.get("amount_currency", False):
            # Percent analytic
            percent_analytic = self[self._budget_analytic_field].get(str(analytic_id))

            budget_vals["amount_currency"] = self.untaxed_amount_currency * (
                percent_analytic / 100
            )
            budget_vals["tax_ids"] = self.tax_ids.ids
        # Document specific vals
        budget_vals.update({"expense_id": self.id})
        return super()._init_docline_budget_vals(budget_vals, analytic_id)

    def _valid_commit_state(self):
        return self.state in ["approved", "done"]

    def _prepare_move_lines_vals(self):
        vals = super()._prepare_move_lines_vals()
        if vals.get("analytic_distribution") and self.fwd_analytic_distribution:
            vals.update({"analytic_distribution": self.fwd_analytic_distribution})
        return vals

    def _get_included_tax(self):
        if self._name == "hr.expense":
            return self.env.company.budget_include_tax_expense
        return super()._get_included_tax()
