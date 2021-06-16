# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    def _where_budget(self):
        """ Monitoring must display latest revision budget """
        where_budget_query = super()._where_budget()
        if where_budget_query:
            where_clause = "and"
        else:
            where_clause = "where"
        budget_control_ids = self.env["budget.control"].search([])
        max_revision = max(budget_control_ids.mapped("revision_number"))
        where_budget_query = "{} ".format(where_clause).join(
            [where_budget_query, "b.revision_number = {}".format(max_revision)]
        )
        return where_budget_query
