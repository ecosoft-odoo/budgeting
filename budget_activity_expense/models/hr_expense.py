# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class HRExpense(models.Model):
    _inherit = "hr.expense"

    @api.onchange("activity_id")
    def _onchange_activity_id(self):
        if self.activity_id:
            self.account_id = self.activity_id.account_id

    @api.depends("product_id", "company_id")
    def _compute_from_product_id_company_id(self):
        res = super()._compute_from_product_id_company_id()
        for expense in self.filtered("activity_id"):
            expense.account_id = expense.activity_id.account_id
        return res

    def _get_account_move_line_values(self):
        move_line_values_by_expense = super()._get_account_move_line_values()
        for expense in self:
            for move_line_values in move_line_values_by_expense[expense.id]:
                if "product_id" in move_line_values:
                    move_line_values["activity_id"] = expense.activity_id.id
        return move_line_values_by_expense
