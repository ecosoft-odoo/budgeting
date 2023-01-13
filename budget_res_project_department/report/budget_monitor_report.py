# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    project_id = fields.Many2one(
        comodel_name="res.project",
    )
    parent_project_name = fields.Char(string="Parent Project")
    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
    )

    # Budget
    def _select_budget(self):
        select_budget_query = super()._select_budget()
        select_budget_query[
            50
        ] = "aa.project_id, rp.parent_project_name, b.department_id"
        return select_budget_query

    def _from_budget(self):
        from_budget_query = super()._from_budget()
        from_budget_query = "\n".join(
            [
                from_budget_query,
                "join account_analytic_account aa on \
                    a.analytic_account_id = aa.id \
                left outer join res_project rp on aa.project_id = rp.id",
            ]
        )
        return from_budget_query

    # All consumed
    def _select_statement(self, amount_type):
        select_statement = super()._select_statement(amount_type)
        select_statement[50] = "aa.project_id, rp.parent_project_name, a.department_id"
        return select_statement

    def _from_statement(self, amount_type):
        from_statment = super()._from_statement(amount_type)
        return "\n".join(
            [
                from_statment,
                "join account_analytic_account aa on \
                    a.analytic_account_id = aa.id \
                left outer join res_project rp on aa.project_id = rp.id",
            ]
        )
