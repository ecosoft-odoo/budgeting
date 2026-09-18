# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    revision_number = fields.Char()

    # Budget
    def _select_budget(self):
        select_budget_query = super()._select_budget()
        select_budget_query[70] = "b.revision_number::text as revision_number"
        return select_budget_query

    # All consumed
    def _select_statement(self, amount_type):
        select_statement = super()._select_statement(amount_type)
        select_statement[70] = "null::text as revision_number"
        return select_statement

    def _select_forward_balance_extra(self):
        select_forward_extra = super()._select_forward_balance_extra()
        select_forward_extra[70] = "null::char as revision_number"
        return select_forward_extra
