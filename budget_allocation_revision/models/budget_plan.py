# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetPlan(models.Model):
    _inherit = "budget.plan"

    def _get_new_rev_data(self, new_rev_number):
        """Update revision budget plan from budget allocation (for change readonly)"""
        self.ensure_one()
        new_rev_number = self._context.get("revision_number", new_rev_number)
        new_rev_dict = super()._get_new_rev_data(new_rev_number)
        new_rev_dict["init_revision"] = False
        return new_rev_dict
