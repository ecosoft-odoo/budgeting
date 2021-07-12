# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class SourceFundMonitorReport(models.Model):
    _inherit = "source.fund.monitor.report"

    def _get_consumed_sources(self):
        return super()._get_consumed_sources() + [
            {
                "model": ("contract.line", "Contract Line"),
                "type": ("6_ct_commit", "CT Commit"),
                "budget_move": ("contract_budget_move", "contract_line_id"),
                "source_doc": ("contract_contract", "contract_id"),
            }
        ]

    def _where_contract(self):
        return ""

    def _get_sql(self):
        select_ct_query = self._select_statement("6_ct_commit")
        key_select_list = sorted(select_ct_query.keys())
        select_ct = ", ".join(select_ct_query[x] for x in key_select_list)
        return super()._get_sql() + "union (select {} {} {})".format(
            select_ct,
            self._from_statement("6_ct_commit"),
            self._where_contract(),
        )
