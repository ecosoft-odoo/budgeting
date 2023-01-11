# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class BudgetActivity(models.Model):
    _inherit = "budget.activity"

    @api.onchange("account_id")
    def _onchange_account_id(self):
        """
        Expense account on product advance depend on account_id activity.
        """
        activity_advance = self.env.ref(
            "budget_activity_advance_clearing.activity_advance"
        )
        if self._origin.id == activity_advance.id:
            emp_advance = self.env.ref(
                "hr_expense_advance_clearing.product_emp_advance"
            )
            emp_advance.property_account_expense_id = self.account_id
