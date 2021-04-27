# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class SourceFundMonitorReport(models.Model):
    _inherit = "source.fund.monitor.report"

    date_from = fields.Date()
    date_to = fields.Date()
    fund_constraint_id = fields.Many2one(comodel_name="fund.constraint")

    # Budget
    def _select_budget(self):
        select_budget_query = super()._select_budget()
        # Replace null analytic and amount
        budget_query = (
            select_budget_query[0]
            .replace(
                "null::integer as analytic_account_id,",
                "aa.id as analytic_account_id,",
            )
            .replace("null::integer as amount", "fc.fund_amount as amount")
        )
        select_budget_query[0] = budget_query
        select_budget_query[
            10
        ] = """
            fc.id as fund_constraint_id,
            aa.bm_date_from as date_from,
            aa.bm_date_to as date_to
        """
        return select_budget_query

    def _from_budget(self):
        from_budget_query = super()._from_budget()
        from_budget_query = "\n".join(
            [
                from_budget_query,
                """
                join fund_constraint fc on fc.fund_id = sf.id
                join account_analytic_account aa
                on aa.id = fc.analytic_account_id
                join budget_control bc
                on bc.analytic_account_id = aa.id
                left join mis_budget_item mbi
                on mbi.budget_control_id = bc.id
                """,
            ]
        )
        return from_budget_query

    def _where_budget(self):
        where_budget_query = super()._where_budget()
        where_budget_query = "and ".join(
            [where_budget_query, "bc.active is true"]
        )
        return where_budget_query

    # All consumed
    def _select_statement(self, amount_type):
        select_statement = super()._select_statement(amount_type)
        select_statement[
            10
        ] = """
            null::integer as fund_constraint_id,
            aa.bm_date_from as date_from,
            aa.bm_date_to as date_to
        """
        return select_statement

    def _from_statement(self, amount_type):
        from_statment = super()._from_statement(amount_type)
        from_statment = "\n".join(
            [
                from_statment,
                """
                join account_analytic_account aa
                on aa.id = a.analytic_account_id
                """,
            ]
        )
        return from_statment
