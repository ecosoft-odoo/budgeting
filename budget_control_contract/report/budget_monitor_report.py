# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    def _get_consumed_sources(self):
        return super()._get_consumed_sources() + [
            {
                "model": ("contract.line", "Contract Line"),
                "type": ("60_ct_commit", "CT Commit"),
                "budget_move": ("contract_budget_move", "contract_line_id"),
                "source_doc": ("contract_contract", "contract_id"),
            }
        ]

    def _where_contract(self):
        visible_company = self.env.context.get("allowed_company_ids")
        if not visible_company:
            return ""

        if len(visible_company) > 1:
            companies = tuple(visible_company)
        else:
            companies = "({})".format(tuple(visible_company)[0])
        return "where a.company_id in {}".format(companies)

    def _get_sql(self):
        select_ct_query = self._select_statement("60_ct_commit")
        key_select_list = sorted(select_ct_query.keys())
        select_ct = ", ".join(select_ct_query[x] for x in key_select_list)
        return super()._get_sql() + "union (select {} {} {})".format(
            select_ct,
            self._from_statement("60_ct_commit"),
            self._where_contract(),
        )
