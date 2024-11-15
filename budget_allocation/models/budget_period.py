# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetPeriod(models.Model):
    _inherit = "budget.period"

    def _get_where_domain(self, analytic_id, template_lines):
        if template_lines._name == "budget.allocation.line":
            unique_fund_ids = template_lines.mapped("fund_id")
            if len(unique_fund_ids) > 1:
                fund_domain = "in {}".format(tuple(unique_fund_ids.ids))
            else:
                fund_domain = "= {}".format(unique_fund_ids.id)
            # Filter where domain budget_period_id for case 1 AA use many period
            return "analytic_account_id = {} and fund_id {} and budget_period_id = {}".format(
                analytic_id, fund_domain, template_lines.budget_period_id.id
            )
        return super()._get_where_domain(analytic_id, template_lines)
