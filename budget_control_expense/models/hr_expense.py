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

    def recompute_budget_move(self):
        budget_field = self._budget_field()
        force_date_commit = self.env.context.get("force_date_commit", False)
        for expense in self:
            # Make sure that date_commit not recompute
            ex_date_commit = force_date_commit or expense.date_commit
            expense[budget_field].unlink()
            expense.with_context(force_date_commit=ex_date_commit).commit_budget()
            # credit will not over debit (auto adjust)
            expense.forward_commit()
        self.mapped(
            "sheet_id.account_move_ids.invoice_line_ids"
        ).uncommit_expense_budget()

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
