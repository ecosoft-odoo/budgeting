# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.tools import SQL


class SourceFundMonitorReport(models.Model):
    _inherit = "budget.source.fund.report"

    @api.model
    def _get_sql(self) -> SQL:
        select_av_query = self._select_statement("40_av_commit")
        key_select_list = sorted(select_av_query.keys())
        select_av = ", ".join(select_av_query[x] for x in key_select_list)
        query_string = super()._get_sql()
        query_string = SQL(
            query_string.code + "UNION ALL (SELECT %(select_av)s %(from_av)s)",
            select_av=SQL(select_av),
            from_av=self._from_statement("40_av_commit"),
        )
        return query_string
