# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    activity = fields.Char(string="Activity")

    # Budget
    def _select_budget(self):
        select_budget_query = super()._select_budget()
        select_budget_query.append("null::char as activity")
        return select_budget_query

    def _from_budget(self):
        from_budget_query = super()._from_budget()
        from_budget_query = "\n".join(
            [
                from_budget_query,
                "join mis_report_kpi_expression mrke on "
                "mbi.kpi_expression_id = mrke.id",
                "join mis_report_kpi mrk on mrke.kpi_id = mrk.id",
            ]
        )
        return from_budget_query

    # All consumed
    def _select_statement(self, amount_type):
        select_statement = super()._select_statement(amount_type)
        select_statement.append("ba.name as activity")
        return select_statement

    def _from_statement(self, amount_type):
        from_statment = super()._from_statement(amount_type)
        return "\n".join(
            [
                from_statment,
                "left outer join budget_activity ba "
                "on a.activity_id = ba.id",
            ]
        )
