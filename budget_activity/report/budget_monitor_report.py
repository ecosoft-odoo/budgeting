# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    activity = fields.Char()

    # Budget
    def _select_budget(self):
        select_budget_query = super()._select_budget()
        # Budget can't find activity
        select_budget_query[20] = "null::char as activity"
        return select_budget_query

    # All consumed
    def _select_statement(self, amount_type):
        select_statement = super()._select_statement(amount_type)
        select_statement[20] = "ba.name as activity"
        return select_statement

    def _get_from_amount_types(self):
        sql_from = super()._get_from_amount_types()
        for sql_from_key in sql_from:
            sql_from[sql_from_key] += (
                "LEFT OUTER JOIN budget_activity ba ON a.activity_id = ba.id\n"
            )
        return sql_from
