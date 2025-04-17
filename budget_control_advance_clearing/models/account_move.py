# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _recompute_budget_return_advance(self):
        """Recompute budget for case return advance"""
        for rec in self:
            if rec.origin_payment_id.advance_id:
                rec.origin_payment_id.advance_id.recompute_budget_move()

    def button_draft(self):
        res = super().button_draft()
        self._recompute_budget_return_advance()
        return res

    def button_cancel(self):
        res = super().button_cancel()
        self._recompute_budget_return_advance()
        return res

    def _reverse_moves(self, default_values_list=None, cancel=False):
        res = super()._reverse_moves(
            default_values_list=default_values_list, cancel=cancel
        )
        self._recompute_budget_return_advance()
        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _condition_skip_uncommit_expense(self, move):
        return (
            move.move_type not in ["in_invoice", "entry"] or not move.expense_sheet_id
        )
