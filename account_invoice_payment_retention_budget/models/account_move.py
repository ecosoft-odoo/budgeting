# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _prepare_retained_move_lines(self, move):
        move_lines = super()._prepare_retained_move_lines(move)
        move_lines["analytic_account_id"] = self.analytic_account_id.id
        move_lines["analytic_tag_ids"] = [(6, 0, self.analytic_tag_ids.ids)]
        return move_lines
