# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    allocation_line_ids = fields.One2many(
        comodel_name="budget.allocation.line",
        inverse_name="analytic_account_id",
    )

    def _check_balance_limit(self, check_lines, dom):
        self.ensure_one()
        # Compute balance limit
        allocation_line_ids = self.allocation_line_ids.filtered_domain(dom)
        budget_amount = allocation_line_ids.mapped("budget_amount")
        balance_limit = sum(budget_amount)
        # Compute balance
        lines = check_lines.filtered_domain(dom)
        amount_balance = [line._get_amount_balance() for line in lines]
        balance = sum(amount_balance)
        if balance > balance_limit:
            raise UserError(
                _(
                    "{} spent amount over limit {:,.2f}".format(
                        self.name, (balance - balance_limit)
                    )
                )
            )
        return True

    def _check_allocation_constraint(self, check_lines):
        self.ensure_one()
        self._check_balance_limit(check_lines, [])
        return True
