# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HRExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"
    _docline_rel = "expense_line_ids"
    _docline_type = "expense"

    budget_move_ids = fields.One2many(
        comodel_name="expense.budget.move",
        inverse_name="sheet_id",
    )

    @api.constrains("expense_line_ids")
    def recompute_budget_move(self):
        self.mapped("expense_line_ids").recompute_budget_move()

    def close_budget_move(self):
        self.mapped("expense_line_ids").close_budget_move()

    def write(self, vals):
        """
        Uncommit the budget when the document state is "approved" or
        when it is canceled/drafted. If the document is canceled or moved to draft,
        all budget commitments will be deleted.

        For expenses, the state is a computed field.
        Therefore, we check the `approval_state` instead:
            - "approve" = Approved
            - "cancel" = Canceled
            - False = To Submit (Draft)
        """
        res = super().write(vals)
        if vals.get("approval_state") in ("approve", "cancel", False):
            doclines = self.mapped("expense_line_ids")
            if vals.get("approval_state") in ("cancel", False):
                doclines.write({"date_commit": False})
            doclines.recompute_budget_move()
        return res

    def unlink(self):
        # Compute commit again after unlink
        expenses = self.mapped("expense_line_ids")
        res = super().unlink()
        expenses._compute_commit()
        return res

    def action_approve_expense_sheets(self):
        res = super().action_approve_expense_sheets()
        BudgetPeriod = self.env["budget.period"]
        for doc in self:
            BudgetPeriod.check_budget(doc.expense_line_ids, doc_type="expense")
        return res

    def action_submit_sheet(self):
        res = super().action_submit_sheet()
        BudgetPeriod = self.env["budget.period"]
        for doc in self:
            BudgetPeriod.check_budget_precommit(
                doc.expense_line_ids, doc_type="expense"
            )
        return res

    def action_sheet_move_create(self):
        res = super().action_sheet_move_create()
        BudgetPeriod = self.env["budget.period"]
        for doc in self:
            BudgetPeriod.check_budget(doc.account_move_ids.line_ids)
        return res


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
