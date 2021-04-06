# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    job_order_id = fields.Many2one(
        comodel_name="budget.job.order",
        string="Job Order",
    )

    # Budget
    def _select_budget(self):
        select_budget_query = super()._select_budget()
        select_budget_query.append("mbi.job_order_id as job_order_id")
        return select_budget_query

    # All consumed
    def _select_statement(self, amount_type):
        select_statement = super()._select_statement(amount_type)
        select_statement.append("a.job_order_id as job_order_id")
        return select_statement
