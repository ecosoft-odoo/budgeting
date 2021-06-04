# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    def _check_allocation_constraint_dimension(self, check_lines):
        self.ensure_one()
        dimension_fields = []
        if check_lines:
            dimension_fields = check_lines[0]._get_dimension_fields()
        for dimension_field in dimension_fields:
            dimensions = check_lines.mapped(dimension_field)
            for dimension in dimensions:
                dom = [(dimension_field, "=", dimension.id)]
                self._check_balance_limit(check_lines, dom)
        return True

    def _check_allocation_constraint(self, check_lines):
        res = super()._check_allocation_constraint(check_lines)
        self._check_allocation_constraint_dimension(check_lines)
        return res
