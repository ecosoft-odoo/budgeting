# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        res = super().action_post()
        for doc in self:
            move_line = doc.line_ids.filtered("fund_id")
            for line in move_line:
                line.check_fund_constraint()
        return res
