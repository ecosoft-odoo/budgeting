# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetMonitorRevisionReport(models.Model):
    _inherit = "budget.monitor.revision.report"

    operating_unit_id = fields.Many2one(comodel_name="operating.unit")

    def _where_budget(self):
        where_sql = super()._where_budget()
        if where_sql:
            where_clause = "and"
        else:
            where_clause = "where"
        operating_unit_ids = self.env.user.operating_unit_ids
        if len(operating_unit_ids) == 1:
            ou = "= {}".format(operating_unit_ids.id)
        else:
            ou = "in {}".format(tuple(operating_unit_ids.ids))
        domain_operating_unit = "{} bc.operating_unit_id {}".format(
            where_clause, ou
        )
        where_query = " ".join([where_sql, domain_operating_unit])
        return where_query

    # Budget
    def _select_budget(self):
        select_budget_query = super()._select_budget()
        select_budget_query[20] = "bc.operating_unit_id"
        return select_budget_query
