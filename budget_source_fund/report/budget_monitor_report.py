# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    fund_id = fields.Many2one(comodel_name="budget.source.fund", string="Fund")
    fund_group_id = fields.Many2one(
        comodel_name="budget.source.fund.group", string="Fund Group"
    )

    # Budget
    def _select_budget(self):
        select_budget_query = super()._select_budget()
        select_budget_query[
            80
        ] = "null::integer as fund_id, null::integer as fund_group_id"
        return select_budget_query

    # All consumed
    def _select_statement(self, amount_type):
        select_statement = super()._select_statement(amount_type)
        select_statement[80] = "a.fund_id, a.fund_group_id"
        return select_statement
