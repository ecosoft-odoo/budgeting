# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    def _get_consumed_sources(self):
        return super()._get_consumed_sources() + [
            {
                "model": ("purchase.request.line", "Purchase Request Line"),
                "type": ("2_pr_commit", "PR Commit"),
                "budget_move": (
                    "purchase_request_budget_move",
                    "purchase_request_line_id",
                ),
                "source_doc": ("purchase_request", "purchase_request_id"),
            }
        ]

    def _get_sql(self):
        select_pr_query = self._select_statement("2_pr_commit")
        select_pr = ", ".join(sorted(select_pr_query))
        return super()._get_sql() + "union (select {} {})".format(
            select_pr,
            self._from_statement("2_pr_commit"),
        )
