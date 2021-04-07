# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class HRExpense(models.Model):
    _name = "hr.expense"
    _inherit = ["hr.expense", "fund.docline.mixin"]
    _amount_balance_field = "total_amount"

    def _get_account_move_line_values(self):
        move_line_values_by_expense = super()._get_account_move_line_values()
        for expense in self:
            fund_dict = {"fund_id": expense.fund_id.id}
            for ml in move_line_values_by_expense[expense.id]:
                if ml.get("product_id"):
                    ml.update(fund_dict)
        return move_line_values_by_expense

    @api.depends("analytic_account_id")
    def _compute_fund_constraint(self):
        super()._compute_fund_constraint()
