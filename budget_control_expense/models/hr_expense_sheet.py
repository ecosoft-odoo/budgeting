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

    def _write(self, vals):
        """
        - UnCommit budget when state post
        - Cancel/Draft document should delete all budget commitment
        """
        res = super()._write(vals)
        if vals.get("state") in ("approve", "post", "cancel", "draft"):
            expense_line = self.mapped("expense_line_ids")
            analytics = expense_line.mapped("analytic_account_id")
            analytics._check_budget_control_status()
            if vals.get("state") == "post":
                expense_line.uncommit_expense_budget()
            else:
                expense_line.commit_budget()
        return res

    def _check_budget_expense(
        self, budget_move_ids, doc_type="expense", amount_precommit=0.0
    ):
        self.ensure_one()
        BudgetPeriod = self.env["budget.period"]
        BudgetPeriod.check_budget(
            budget_move_ids,
            doc_type=doc_type,
            amount_precommit=amount_precommit,
        )

    def approve_expense_sheets(self):
        res = super().approve_expense_sheets()
        self.flush()
        for sheet in self:
            sheet._check_budget_expense(sheet.budget_move_ids)
        return res

    def action_submit_sheet(self):
        res = super().action_submit_sheet()
        self.flush()
        for sheet in self:
            sheet._check_budget_expense(
                sheet.expense_line_ids, amount_precommit=sheet.total_amount
            )
        return res
