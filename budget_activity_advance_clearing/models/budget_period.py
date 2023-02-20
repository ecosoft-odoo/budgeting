# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetPeriod(models.Model):
    _inherit = "budget.period"

    def _get_budget_avaiable(self, analytic_id, template_lines):
        """Not check budget available with kpi advance"""
        kpi_advance = self.env.ref(
            "budget_activity_advance_clearing.budget_kpi_advance"
        )
        if template_lines._name == "budget.template.line":
            template_lines = template_lines.filtered(lambda l: l.kpi_id != kpi_advance)
        return super()._get_budget_avaiable(analytic_id, template_lines)
