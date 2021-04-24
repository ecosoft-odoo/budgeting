# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetMonitorRevisionReport(models.Model):
    _inherit = "budget.monitor.revision.report"

    department_id = fields.Many2one(comodel_name="hr.department")

    def _select_budget(self):
        select_budget_query = super()._select_budget()
        select_budget_query[30] = "bc.department_id"
        return select_budget_query
