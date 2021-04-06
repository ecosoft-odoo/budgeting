# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = ["purchase.request", "base.fund.constraint.commit"]
    _doc_line_field = "line_ids"

    def button_to_approve(self):
        res = super().button_to_approve()
        self.check_fund_constraint()
        return res
