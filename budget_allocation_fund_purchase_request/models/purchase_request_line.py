# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    # Trigger analytic
    @api.depends("analytic_account_id")
    def _compute_fund_all(self):
        super()._compute_fund_all()
