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
