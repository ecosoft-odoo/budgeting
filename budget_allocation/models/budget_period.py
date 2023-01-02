# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models


class BudgetPeriod(models.Model):
    _inherit = "budget.period"

    def _get_where_domain(self, analytic_id, template_lines):
        if template_lines._name == "budget.allocation.line":
            template_line_domain = (
                "= {}".format(template_lines.id)
                if len(template_lines) == 1
                else "in {}".format(tuple(template_lines.ids))
            )
            return "analytic_account_id = {} and fund_id {}".format(
                analytic_id, template_line_domain
            )
        return super()._get_where_domain(analytic_id, template_lines)
