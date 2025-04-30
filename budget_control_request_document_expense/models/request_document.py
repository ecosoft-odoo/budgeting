# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class RequestDocument(models.Model):
    _inherit = "request.document"

    def _get_exp_value(self, exp):
        exp_value = super()._get_exp_value(exp)
        if exp.fwd_analytic_account_id:
            exp_value["analytic_account_id"] = exp.fwd_analytic_account_id.id
        return exp_value


class RequestDocumentExpenseLine(models.Model):
    _name = "request.document.expense.line"
    _inherit = ["request.document.expense.line", "budget.docline.mixin"]
    _budget_date_commit_fields = ["document_id.write_date"]
    _budget_move_model = "request.budget.move"
    _doc_rel = "document_id"
    _description = "Request Document Budget Expense Line"

    budget_move_ids = fields.One2many(
        comodel_name="request.budget.move",
        inverse_name="expense_request_line_id",
        string="Request Budget Moves",
    )

    def uncommit_origin_budget(self):
        return

    def recompute_budget_move(self):
        for line in self:
            line.budget_move_ids.unlink()
            line.commit_budget()
            # credit will not over debit (auto adjust)
            line.forward_commit()
            line.uncommit_origin_budget()
            sheet = line.document_id.expense_sheet_ids
            if (
                line.document_id.state in ("approve", "done")
                and sheet.budget_move_ids
                and sheet.state in ["approve", "post", "done"]
            ):
                line.close_budget_move()

    def _init_docline_budget_vals(self, budget_vals):
        self.ensure_one()
        if self._name == "request.document.expense.line":
            if not budget_vals.get("amount_currency", False):
                budget_vals["amount_currency"] = (
                    (self.quantity * self.unit_amount)
                    if self.product_has_cost
                    else self.total_amount
                )
                budget_vals["tax_ids"] = self.tax_ids.ids
            # Document specific vals
            budget_vals.update(
                {
                    "expense_request_line_id": self.id,
                    "request_document_id": self.document_id.id,
                    "analytic_tag_ids": [(6, 0, self.analytic_tag_ids.ids)],
                }
            )
            return budget_vals
        return super()._init_docline_budget_vals(budget_vals)

    def _valid_commit_state(self):
        return self.document_id.state in ["approve", "done"]
