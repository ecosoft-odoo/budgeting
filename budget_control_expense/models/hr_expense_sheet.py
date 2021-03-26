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

    # def _write(self, vals):  TODO: using _write() seem not ok for test script
    def write(self, vals):
        """
        - UnCommit budget when state post
        - Cancel/Draft document should delete all budget commitment
        """
        res = super().write(vals)
        if vals.get("state") in ("approve", "cancel", "draft"):
            self.mapped("expense_line_ids").commit_budget()
        return res

    def approve_expense_sheets(self):
        res = super().approve_expense_sheets()
        self.flush()
        BudgetPeriod = self.env["budget.period"]
        for doc in self:
            BudgetPeriod.check_budget(doc.budget_move_ids, doc_type="expense")
        return res

    def action_submit_sheet(self):
        res = super().action_submit_sheet()
        self.flush()
        BudgetPeriod = self.env["budget.period"]
        for doc in self:
            BudgetPeriod.check_budget(
                doc.expense_line_ids,
                doc_type="expense",
                amount_precommit=doc.total_amount,
            )
        return res
