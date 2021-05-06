# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    def _get_m2o_fields(self):
        if self.env.context.get("update_custom_fields"):
            return []  # Avoid to report these columns when not yet created
        return [x for x in self.fields_get().keys() if x.startswith("x_m2o_")]

    # Budget
    def _select_budget(self):
        select_budget_query = super()._select_budget()
        add_fields = self._get_m2o_fields()
        add_fields = ["0 as {}".format(x) for x in add_fields]
        if add_fields:
            select_budget_query[60] = ", ".join(add_fields)
        return select_budget_query

    # All consumed
    def _select_statement(self, amount_type):
        select_statement = super()._select_statement(amount_type)
        add_fields = self._get_m2o_fields()
        add_fields = ["a.{0} as {0}".format(x) for x in add_fields]
        if add_fields:
            select_statement[60] = ", ".join(add_fields)
        return select_statement
