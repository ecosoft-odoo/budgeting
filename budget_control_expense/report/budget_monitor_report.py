# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.tools import SQL


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    def _get_consumed_sources(self):
        return super()._get_consumed_sources() + [
            {
                "model": ("hr.expense", "Expense"),
                "type": ("50_ex_commit", "EX Commit"),
                "budget_move": ("expense_budget_move", "expense_id"),
                "source_doc": ("hr_expense_sheet", "sheet_id"),
            }
        ]

    @api.model
    def _where_expense(self) -> SQL:
        return SQL("")

    @api.model
    def _get_sql(self) -> SQL:
        select_ex_query = self._select_statement("50_ex_commit")
        key_select_list = sorted(select_ex_query.keys())
        select_ex = ", ".join(select_ex_query[x] for x in key_select_list)
        query_string = super()._get_sql()
        query_string = SQL(
            query_string.code
            + "UNION ALL (SELECT %(select_ex)s %(from_ex)s %(where_ex)s)",
            select_ex=SQL(select_ex),
            from_ex=self._from_statement("50_ex_commit"),
            where_ex=self._where_expense(),
        )
        return query_string
