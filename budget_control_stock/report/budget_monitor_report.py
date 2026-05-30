# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.tools import SQL


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    @api.model
    def _where_stock(self) -> SQL:
        return SQL("")

    @api.model
    def _get_sql(self) -> SQL:
        select_st_query = self._select_statement("75_st_commit")
        key_select_list = sorted(select_st_query.keys())
        select_st = ", ".join(select_st_query[x] for x in key_select_list)
        query_string = super()._get_sql()
        query_string = SQL(
            query_string.code
            + "UNION ALL (SELECT %(select_st)s %(from_st)s %(where_st)s)",
            select_st=SQL(select_st),
            from_st=self._from_statement("75_st_commit"),
            where_st=self._where_stock(),
        )
        return query_string
