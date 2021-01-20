# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class HRExpense(models.Model):
    _inherit = "hr.expense"

    advance_budget_move_ids = fields.One2many(
        comodel_name="advance.budget.move",
        inverse_name="expense_id",
    )

    def _budget_move_create(self, vals):
        self.ensure_one()
        new_vals = vals.copy()
        if not self.advance and not self.clearing:
            return super()._budget_move_create(vals)
        if self.advance:
            budget_move = self.env["advance.budget.move"].create(new_vals)
            return budget_move
        # Case : Clearing, we should decrease budget advance before increase
        budget_move = False
        advance_clearing = self.sheet_id.advance_sheet_id
        if new_vals["debit"] and advance_clearing:
            expense_id = advance_clearing.expense_line_ids[0]
            new_vals["credit"] = new_vals["debit"]
            new_vals["debit"] = 0.0
            # Updated on advance
            new_vals["activity_id"] = expense_id.activity_id.id
            budget_move = self.env["advance.budget.move"].create(new_vals)
        super()._budget_move_create(vals)
        return budget_move

    def _budget_move_unlink(self):
        self.ensure_one()
        if not self.advance and not self.clearing:
            return super()._budget_move_unlink()
        if self.clearing:
            super()._budget_move_unlink()
        return self.advance_budget_move_ids.unlink()

    def _search_domain_expense(self):
        domain = super()._search_domain_expense()
        domain = domain and not self.advance
        return domain
