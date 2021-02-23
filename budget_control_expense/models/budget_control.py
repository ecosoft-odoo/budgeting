# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    expense_amount = fields.Monetary(
        string="Expense Amount",
        compute="_compute_expense_amount",
        help="Sum of expense amount",
    )

    @api.depends("item_ids")
    def _compute_expense_amount(self):
        ExpenseBudgetMove = self.env["expense.budget.move"]
        for rec in self:
            ex_move = ExpenseBudgetMove.search(
                [("analytic_account_id", "=", rec.analytic_account_id.id)]
            )
            expense_amount = sum(ex_move.mapped("debit"))
            rec.expense_amount = expense_amount or 0.0
