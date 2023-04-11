# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    def _get_consumed_sources(self):
        return super()._get_consumed_sources() + [
            {
                "model": ("purchase.order.line", "Purchase Line"),
                "type": ("7_agreement_commit", "Agreement Commit"),
                "budget_move": ("purchase_budget_move", "purchase_line_id"),
                "source_doc": ("purchase_order", "purchase_id"),
            }
        ]

    def _where_purchase(self):
        """Overwrite split commit purchase to purchase and agreement"""
        where_purchase = "where a.is_agreement is not true"
        if self._context.get("is_agreement", False):
            where_purchase = "where a.is_agreement"
        return where_purchase

    def _get_sql(self):
        type_commit = "7_agreement_commit"
        select_po_query = self._select_statement(type_commit)
        key_select_list = sorted(select_po_query.keys())
        select_po = ", ".join(select_po_query[x] for x in key_select_list)
        return super()._get_sql() + "union (select {} {} {})".format(
            select_po,
            self._from_statement(type_commit),
            self.with_context(is_agreement=1)._where_purchase(),
        )
