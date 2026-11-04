# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    activity_id = fields.Many2one(
        comodel_name="budget.activity",
    )

    def _select_forward_balance_extra(self):
        select = super()._select_forward_balance_extra()
        select[20] = "NULL::integer AS activity_id"
        return select

    # Budget
    def _select_budget(self):
        select = super()._select_budget()
        # Budgets are planned by KPI, not by activity
        select[20] = "NULL::integer AS activity_id"
        return select

    # All consumed
    def _select_statement(self, amount_type):
        select = super()._select_statement(amount_type)
        select[20] = "a.activity_id"
        return select
