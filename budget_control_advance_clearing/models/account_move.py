# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def reconcile(self):
        res = super().reconcile()
        # Case return advance, when advance is cleared to zero, close budget move
        # Note: only support case cleared to zero, not partial
        advance_sheets = self.filtered("expense_id.advance").mapped(
            "expense_id.sheet_id"
        )
        advance_sheets = advance_sheets.filtered(
            lambda l: not l.clearing_residual
        )
        advance_sheets.close_budget_move()
        return res

    def write(self, vals):
        """
        - Add context skip_account_move_synchronization on move line account advance
        """
        move_lines = self.move_id.mapped(
            "line_ids"
        )  # make sure any moveline is advance
        emp_advance = self.env.ref(
            "hr_expense_advance_clearing.product_emp_advance"
        )
        expense_advance_id = emp_advance.property_account_expense_id.id
        ml_advance = move_lines.filtered(
            lambda l: l.account_id.id == expense_advance_id
        )
        if ml_advance:
            self = self.with_context(skip_account_move_synchronization=True)
        return super().write(vals)
