# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


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

    def _where_purchase(self):
        visible_company = self.env.context.get("allowed_company_ids")
        if not visible_company:
            return ""

        if len(visible_company) > 1:
            companies = tuple(visible_company)
        else:
            companies = "({})".format(tuple(visible_company)[0])
        return "where a.company_id in {}".format(companies)

    def _get_sql(self):
        select_po_query = self._select_statement("30_po_commit")
        key_select_list = sorted(select_po_query.keys())
        select_po = ", ".join(select_po_query[x] for x in key_select_list)
        return super()._get_sql() + "union (select {} {} {})".format(
            select_po,
            self._from_statement("30_po_commit"),
            self._where_purchase(),
        )
