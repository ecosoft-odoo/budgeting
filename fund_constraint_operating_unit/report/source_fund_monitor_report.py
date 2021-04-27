# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class SourceFundMonitorReport(models.Model):
    _inherit = "source.fund.monitor.report"

    operating_unit_id = fields.Many2one(comodel_name="operating.unit")

    def _get_where_sql(self):
        where_sql = super()._get_where_sql()
        if where_sql:
            where_clause = "and"
        else:
            where_clause = "where"
        operating_unit_ids = self.env.user.operating_unit_ids
        if len(operating_unit_ids) == 1:
            ou = "= {}".format(operating_unit_ids.id)
        else:
            ou = "in {}".format(tuple(operating_unit_ids.ids))
        domain_operating_unit = "{} a.operating_unit_id {}".format(
            where_clause, ou
        )
        where_query = " ".join([where_sql, domain_operating_unit])
        return where_query

    # Budget
    def _select_budget(self):
        select_budget_query = super()._select_budget()
        select_budget_query[30] = "bc.operating_unit_id"
        return select_budget_query

    # All consumed
    def _select_statement(self, amount_type):
        select_statement = super()._select_statement(amount_type)
        select_statement[30] = "b.operating_unit_id"
        return select_statement
