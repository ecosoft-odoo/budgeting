# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetMonitorRevisionReport(models.Model):
    _name = "budget.monitor.revision.report"
    _inherit = "budget.monitor.report"
    _description = "Budget Revision Monitoring Report"
    _auto = False
    _order = "date desc"
    _rec_name = "reference"

    def _from_budget(self):
        """To see the previous version, active can be false."""
        sql_from = super()._from_budget()
        return sql_from.replace("and b.active = true", "")

    def _get_sql(self):
        """Not query commitment in revision monitoring"""
        select_budget_query = self._select_budget()
        key_select_budget_list = sorted(select_budget_query.keys())
        select_budget = ", ".join(
            select_budget_query[x] for x in key_select_budget_list
        )
        return "(select {} {})".format(
            select_budget,
            self._from_budget(),
        )
