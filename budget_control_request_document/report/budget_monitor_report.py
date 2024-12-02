# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    def _get_consumed_sources(self):
        return super()._get_consumed_sources() + [
            {
                "model": ("request.document", "Request"),
                "type": ("15_rq_commit", "Request Commit"),
                "budget_move": ("request_budget_move", "request_document_id"),
                "source_doc": ("request_request", "request_id"),
            }
        ]

    def _where_expense(self):
        return ""

    def _get_sql(self):
        select_ex_query = self._select_statement("15_rq_commit")
        key_select_list = sorted(select_ex_query.keys())
        select_ex = ", ".join(select_ex_query[x] for x in key_select_list)
        return super()._get_sql() + "union (select {} {} {})".format(
            select_ex,
            self._from_statement("15_rq_commit"),
            self._where_expense(),
        )
