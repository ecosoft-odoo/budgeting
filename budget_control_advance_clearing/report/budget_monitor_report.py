# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.tools import SQL


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    def _get_consumed_sources(self):
        return super()._get_consumed_sources() + [
            {
                "model": ("hr.expense", "Expense"),
                "type": ("40_av_commit", "AV Commit"),
                "budget_move": ("advance_budget_move", "expense_id"),
                "source_doc": ("hr_expense_sheet", "sheet_id"),
            }
        ]

    def _where_advance_clearing(self) -> SQL:
        return SQL("")

    def _get_sql(self) -> SQL:
        select_av_query = self._select_statement("40_av_commit")
        key_select_list = sorted(select_av_query.keys())
        select_av = ", ".join(select_av_query[x] for x in key_select_list)
        query_string = super()._get_sql()
        query_string = SQL(
            query_string.code
            + "UNION ALL (SELECT %(select_av)s %(from_av)s %(where_av)s)",
            select_av=SQL(select_av),
            from_av=self._from_statement("40_av_commit"),
            where_av=self._where_advance_clearing(),
        )
        return query_string
