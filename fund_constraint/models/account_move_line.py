# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    _amount_balance_field = "balance"

    # Trigger analytic
    @api.depends("analytic_account_id")
    def _compute_fund_constraint(self):
        super()._compute_fund_constraint()
