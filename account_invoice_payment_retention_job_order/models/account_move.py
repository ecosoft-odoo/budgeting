# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _prepare_retained_move_lines(self, move):
        move_lines = super()._prepare_retained_move_lines(move)
        move_lines["job_order_id"] = self.job_order_id.id
        return move_lines
