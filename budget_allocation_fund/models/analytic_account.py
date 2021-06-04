# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    def _check_allocation_constraint_fund(self, check_lines):
        self.ensure_one()
        funds = check_lines.mapped("fund_id")
        for fund in funds:
            dom = [("fund_id", "=", fund.id)]
            self._check_balance_limit(check_lines, dom)
        return True

    def _check_allocation_constraint(self, check_lines):
        res = super()._check_allocation_constraint(check_lines)
        self._check_allocation_constraint_fund(check_lines)
        return res
