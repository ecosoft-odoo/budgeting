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
