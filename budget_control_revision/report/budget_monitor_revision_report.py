# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.tools import SQL


class BudgetMonitorRevisionReport(models.Model):
    _name = "budget.monitor.revision.report"
    _inherit = "budget.monitor.report"
    _description = "Budget Revision Monitoring Report"
    _auto = False
    _order = "date desc"
    _rec_name = "reference"

    @api.model
    def _from_budget(self) -> SQL:
        """To see the previous version, active can be false."""
        sql_from = super()._from_budget()
        sql_from = sql_from.code.replace("WHERE b.active = TRUE", "")
        return SQL(sql_from)

    @api.model
    def _get_sql(self) -> SQL:
        """Not query commitment in revision monitoring"""
        select_budget_query = self._select_budget()
        key_select_budget_list = sorted(select_budget_query.keys())
        select_budget = ", ".join(
            select_budget_query[x] for x in key_select_budget_list
        )
        return SQL(
            """
            (SELECT %(select_budget)s %(from_budget)s)
            """,
            select_budget=SQL(select_budget),
            from_budget=self._from_budget(),
        )
