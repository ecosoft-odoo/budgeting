# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.tools import SQL


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    @api.model
    def _where_request(self) -> SQL:
        return SQL("")

    def _get_sql(self) -> SQL:
        select_request_query = self._select_statement("15_rq_commit")
        key_select_list = sorted(select_request_query.keys())
        select_request = ", ".join(select_request_query[x] for x in key_select_list)
        query_string = super()._get_sql()
        query_string = SQL(
            query_string.code
            + "UNION ALL (SELECT %(select_req)s %(from_req)s %(where_req)s)",
            select_req=SQL(select_request),
            from_req=self._from_statement("15_rq_commit"),
            where_req=self._where_request(),
        )
        return query_string
