# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class HRExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    advance_budget_move_ids = fields.One2many(
        comodel_name="advance.budget.move",
        inverse_name="sheet_id",
    )

    # def _write(self, vals):  TODO: using _write() seem not ok for test script
    def write(self, vals):
        res = super().write(vals)
        expense_line = self.mapped("expense_line_ids")
        if vals.get("state") == "done" and vals.get("advance_sheet_residual"):
            expense_line.uncommit_expense_budget()
        return res

    def approve_expense_sheets(self):
        res = super().approve_expense_sheets()
        self.flush()
        for sheet in self:
            if sheet.advance:
                sheet._check_budget_expense(
                    sheet.advance_budget_move_ids, doc_type="advance"
                )
        return res

    def recompute_advance_budget_move(self):
        self.mapped("advance_budget_move_ids").unlink()
        self.commit_budget()
        self.uncommit_expense_budget()
