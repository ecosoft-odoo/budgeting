# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class HRExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def action_submit_sheet(self):
        res = super().action_submit_sheet()
        for doc in self:
            exp_line = doc.expense_line_ids.filtered("fund_id")
            for line in exp_line:
                line.check_fund_constraint()
        return res
