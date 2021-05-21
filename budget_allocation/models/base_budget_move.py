# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetDoclineMixin(models.AbstractModel):
    _inherit = "budget.docline.mixin"
    _amount_balance_field = False

    def _get_amount_balance(self):
        self.ensure_one()
        if not self._amount_balance_field:
            return 0.0
        return self[self._amount_balance_field]

    def check_allocation_constraint(self):
        analytics = self.mapped(self._budget_analytic_field)
        for analytic in analytics:
            check_lines = self.filtered(
                lambda l: l[l._budget_analytic_field] == analytic.id
            )
            analytic._check_allocation_constraint(check_lines)
        return True
