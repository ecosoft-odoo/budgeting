# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class HRExpenseSheet(models.Model):
    _name = "hr.expense.sheet"
    _inherit = ["hr.expense.sheet", "base.fund.constraint.commit"]
    _doc_line_field = "expense_line_ids"

    def action_submit_sheet(self):
        res = super().action_submit_sheet()
        self.check_fund_constraint()
        return res
