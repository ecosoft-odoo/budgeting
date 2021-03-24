# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    def _get_consumed_sources(self):
        return super()._get_consumed_sources() + [
            {
                "model": ("hr.expense", "Expense"),
                "type": ("4_av_commit", "AV Commit"),
                "budget_move": ("advance_budget_move", "expense_id"),
                "source_doc": ("hr_expense_sheet", "sheet_id"),
            }
        ]

    def _get_sql(self):
        select_av_query = self._select_statement("4_av_commit")
        select_av = ", ".join(sorted(select_av_query))
        return super()._get_sql() + "union (select {} {})".format(
            select_av,
            self._from_statement("4_av_commit"),
        )
