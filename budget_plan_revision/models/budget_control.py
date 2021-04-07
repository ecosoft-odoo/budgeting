# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    _sql_constraints = [
        (
            "name_uniq",
            "UNIQUE(name, revision_number, active)",
            "Name must be unique!",
        ),
        (
            "budget_control_uniq",
            "UNIQUE(budget_id, analytic_account_id, revision_number, active)",
            "Duplicated analytic account for the same budget!",
        ),
    ]

    def _get_new_rev_data(self, new_rev_number):
        """ Update revision budget control from budget plan """
        self.ensure_one()
        new_rev_number = self._context.get("revision_number", new_rev_number)
        return super()._get_new_rev_data(new_rev_number)
