# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetMonitorRevisionReport(models.Model):
    _inherit = "budget.monitor.revision.report"

    project_id = fields.Many2one(comodel_name="res.project", index=True)

    def _select_budget(self):
        select_budget_query = super()._select_budget()
        select_budget_query[40] = "aa.project_id"
        return select_budget_query

    def _from_budget(self):
        from_budget_query = super()._from_budget()
        from_budget_query = "\n".join(
            [
                from_budget_query,
                "join account_analytic_account aa on bc.analytic_account_id = aa.id",
            ]
        )
        return from_budget_query
