# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "base.fund.constraint.commit"]
    _doc_line_field = "line_ids"

    def action_post(self):
        res = super().action_post()
        self.check_fund_constraint()
        return res
