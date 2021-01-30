# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def _prepare_expense_clearing(self):
        expense_vals = super()._prepare_expense_clearing()
        for i, line in enumerate(self.advance_line):
            expense_vals[i]["operating_unit_id"] = line.operating_unit_id.id
        return expense_vals
