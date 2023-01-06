# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    def _get_pr_line_account(self):
        if self.activity_id:
            return self.activity_id.account_id
        return super()._get_pr_line_account()
