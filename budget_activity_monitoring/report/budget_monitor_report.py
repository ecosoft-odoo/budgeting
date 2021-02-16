# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    activity_group = fields.Char(string="Activity Group")
    activity = fields.Char(string="Activity")

    # Budget
    def _select_budget(self):
        select_budget_query = super()._select_budget()
        select_budget_query = ",".join(
            [
                select_budget_query,
                "mrk.description as activity_group, null::char as activity",
            ]
        )
        return select_budget_query

    def _from_budget(self):
        from_budget_query = super()._from_budget()
        from_budget_query = "\n".join(
            [
                from_budget_query,
                "join mis_report_kpi_expression mrke \
                    on mbi.kpi_expression_id = mrke.id",
                "join mis_report_kpi mrk on mrke.kpi_id = mrk.id",
            ]
        )
        return from_budget_query

    # Actual
    def _select_actual(self):
        select_actual_query = super()._select_actual()
        select_actual_query = ",".join(
            [
                select_actual_query,
                "bag.name as activity_group, ba.name as activity",
            ]
        )
        return select_actual_query

    def _from_actual(self):
        from_actual_query = super()._from_actual()
        from_actual_query = "\n".join(
            [
                from_actual_query,
                "left outer join budget_activity ba \
                    on a.activity_id = ba.id",
                "left outer join budget_activity_group bag \
                    on ba.activity_group_id = bag.id",
            ]
        )
        return from_actual_query
