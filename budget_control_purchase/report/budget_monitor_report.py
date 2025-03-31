# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.tools import SQL


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    def _get_consumed_sources(self):
        return super()._get_consumed_sources() + [
            {
                "model": ("purchase.order.line", "Purchase Line"),
                "type": ("30_po_commit", "PO Commit"),
                "budget_move": ("purchase_budget_move", "purchase_line_id"),
                "source_doc": ("purchase_order", "purchase_id"),
            }
        ]

    @api.model
    def _where_purchase(self) -> SQL:
        return SQL("")

    @api.model
    def _get_sql(self) -> SQL:
        select_po_query = self._select_statement("30_po_commit")
        key_select_list = sorted(select_po_query.keys())
        select_po = ", ".join(select_po_query[x] for x in key_select_list)
        query_string = super()._get_sql()
        query_string = SQL(
            query_string.code
            + "UNION ALL (SELECT %(select_po)s %(from_po)s %(where_po)s)",
            select_po=SQL(select_po),
            from_po=self._from_statement("30_po_commit"),
            where_po=self._where_purchase(),
        )
        return query_string
