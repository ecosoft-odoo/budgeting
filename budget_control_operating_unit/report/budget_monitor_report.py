# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    operating_unit_id = fields.Many2one(comodel_name="operating.unit")

    # Budget
    def _select_budget(self):
        select_budget_query = super()._select_budget()
        select_budget_query.append("b.operating_unit_id")
        return select_budget_query

    # All consumed
    def _select_statement(self, amount_type):
        select_statement = super()._select_statement(amount_type)
        select_statement.append("b.operating_unit_id")
        return select_statement
