# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        res = super().action_post()
        self.flush()
        for move in self._filtered_move_check_budget():
            move.line_ids.check_allocation_constraint()
        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    _amount_balance_field = "balance"
