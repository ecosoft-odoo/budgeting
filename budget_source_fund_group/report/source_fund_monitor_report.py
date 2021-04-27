# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class SourceFundMonitorReport(models.Model):
    _inherit = "source.fund.monitor.report"

    fund_group_id = fields.Many2one(comodel_name="budget.source.fund.group")

    # Budget
    def _select_budget(self):
        select_budget_query = super()._select_budget()
        select_budget_query[20] = "sf_group.id as fund_group_id"
        return select_budget_query

    def _from_budget(self):
        from_budget_query = super()._from_budget()
        from_budget_query = "\n".join(
            [
                from_budget_query,
                "join budget_source_fund_group sf_group "
                "on sf_group.id = sf.fund_group_id",
            ]
        )
        return from_budget_query

    # All consumed
    def _select_statement(self, amount_type):
        select_statement = super()._select_statement(amount_type)
        select_statement[20] = "sf_group.id as fund_group_id"
        return select_statement

    def _from_statement(self, amount_type):
        from_statment = super()._from_statement(amount_type)
        from_statment = "\n".join(
            [
                from_statment,
                "join budget_source_fund_group sf_group "
                "on sf_group.id = sf.fund_group_id",
            ]
        )
        return from_statment
