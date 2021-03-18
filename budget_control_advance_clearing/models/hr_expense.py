# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class HRExpense(models.Model):
    _inherit = "hr.expense"

    advance_budget_move_ids = fields.One2many(
        comodel_name="advance.budget.move",
        inverse_name="expense_id",
    )

    @api.depends(
        "budget_move_ids", "budget_move_ids.date", "advance_budget_move_ids"
    )
    def _compute_amount_commit(self):
        for rec in self:
            if rec.advance_budget_move_ids:
                advance_id = rec.sheet_id.advance_sheet_id
                # advance
                if not advance_id:
                    debit = sum(rec.advance_budget_move_ids.mapped("debit"))
                    credit = sum(rec.advance_budget_move_ids.mapped("credit"))
                    rec.amount_commit = debit - credit
                    continue
                # commit advance previous
                debit = sum(advance_id.advance_budget_move_ids.mapped("debit"))
                credit = sum(
                    advance_id.advance_budget_move_ids.mapped("credit")
                )
                total_clearing = debit - credit
                advance_id.expense_line_ids.amount_commit -= total_clearing
                # commit clearing
                debit = sum(rec.budget_move_ids.mapped("debit"))
                credit = sum(rec.budget_move_ids.mapped("credit"))
                rec.amount_commit = debit - credit
            else:
                super()._compute_amount_commit()

    def _budget_move_create(self, vals):
        """
        Case Expense
        - Increase expense on expense
        Case Advance
        - Increase advance on employee advance
        Case Clearing
        - Decrease advance on origin employee advance
        - Increase expense on expense
        """
        self.ensure_one()
        new_vals = vals.copy()
        sheet_advance = self.sheet_id.advance_sheet_id  # clearing
        if not self.advance and not sheet_advance:
            return super()._budget_move_create(vals)
        if self.advance:
            budget_move = self.env["advance.budget.move"].create(new_vals)
            return budget_move
        budget_move = False
        expense_advance = sheet_advance.expense_line_ids
        if expense_advance and new_vals["debit"]:
            new_vals["credit"] = new_vals["debit"]
            new_vals["debit"] = 0.0
            new_vals["activity_id"] = expense_advance.activity_id.id
            budget_move = self.env["advance.budget.move"].create(new_vals)
        super()._budget_move_create(vals)
        return budget_move

    def _budget_move_unlink(self):
        self.ensure_one()
        sheet_advance = self.sheet_id.advance_sheet_id  # clearing
        if not self.advance and not sheet_advance:
            return super()._budget_move_unlink()
        if sheet_advance:
            super()._budget_move_unlink()
        return self.advance_budget_move_ids.unlink()

    def _search_domain_expense(self):
        domain = super()._search_domain_expense()
        domain = domain and not self.advance
        return domain
