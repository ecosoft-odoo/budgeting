# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    activity_group = fields.Char(string="Activity Group")

    # Budget
    def _select_budget(self):
        select_budget_query = super()._select_budget()
        select_budget_query.append("mrk.description as activity_group")
        return select_budget_query

    # All consumed
    def _select_statement(self, amount_type):
        select_statement = super()._select_statement(amount_type)
        select_statement.append("bag.name as activity_group")
        return select_statement

    def _from_statement(self, amount_type):
        from_statment = super()._from_statement(amount_type)
        return "\n".join(
            [
                from_statment,
                "left outer join budget_activity_group bag "
                "on ba.activity_group_id = bag.id",
            ]
        )
