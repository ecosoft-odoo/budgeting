# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class BudgetActivity(models.Model):
    _inherit = "budget.activity"

    @api.onchange("account_id")
    def _onchange_account_id(self):
        """
        Update the expense account of the employee advance product based on the
        account_id activity of the current record.
        """
        budget_activity_advance = self.env.ref(
            "budget_activity_advance_clearing.budget_activity_advance"
        )
        # If the current record is the budget activity advance reference
        if self._origin.id == budget_activity_advance.id:
            employee_advance_product = self.env.ref(
                "hr_expense_advance_clearing.product_emp_advance"
            )
            # Update the expense account of the employee advance product
            employee_advance_product.update(
                {"property_account_expense_id": self.account_id}
            )
