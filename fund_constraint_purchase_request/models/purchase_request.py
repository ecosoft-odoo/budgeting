# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    def button_to_approve(self):
        res = super().button_to_approve()
        for doc in self:
            pr_line = doc.line_ids.filtered("fund_id")
            for line in pr_line:
                line.check_fund_constraint()
        return res
