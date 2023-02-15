# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetPeriod(models.Model):
    _inherit = "budget.period"

    def _get_where_domain(self, analytic_id, template_lines):
        if template_lines._name == "budget.allocation.line":
            fund_domain = (
                "= {}".format(template_lines.fund_id.id)
                if len(template_lines) == 1
                else "in {}".format(tuple(template_lines.mapped("fund_id").ids))
            )
            return "analytic_account_id = {} and fund_id {}".format(
                analytic_id, fund_domain
            )
        return super()._get_where_domain(analytic_id, template_lines)
