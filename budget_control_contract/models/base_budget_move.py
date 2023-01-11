# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetDoclineMixin(models.AbstractModel):
    _inherit = "budget.docline.mixin"

    def _update_budget_commitment(self, budget_vals, reverse=False):
        """Update date is not range in analytic account"""
        self.ensure_one()
        budget_vals = super()._update_budget_commitment(budget_vals, reverse)
        if self._budget_model() == "contract.budget.move":
            if (
                budget_vals["date"] <= self.analytic_account_id.bm_date_from
                or budget_vals["date"] >= self.analytic_account_id.bm_date_to
            ):
                budget_vals["date"] = self.analytic_account_id.bm_date_from
        return budget_vals
