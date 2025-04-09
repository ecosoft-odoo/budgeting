# Copyright 2022 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import models


class AccountAnalyticTag(models.Model):
    _inherit = "account.analytic.tag"

    def _check_required_dimension(self, record):
        """Skip check dimension if not affect budget and period budget is not control"""
        record.ensure_one()
        not_affect_budget = False
        if record._name == "account.move.line":
            not_affect_budget = record.move_id.not_affect_budget
        elif record._name == "account.analytic.line":
            not_affect_budget = record.move_id.move_id.not_affect_budget
        # field has analytic account, check control_budget in budget_period
        if hasattr(record, "_budget_analytic_field"):
            date = record[record._budget_analytic_field].bm_date_to
            period = self.env["budget.period"]._get_eligible_budget_period(date)
            if not period.control_budget:
                not_affect_budget = True
        # not affect budget = not check dimension
        if not_affect_budget:
            return
        return super()._check_required_dimension(record)
