# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SourceFundMonitorReport(models.Model):
    _inherit = "source.fund.monitor.report"

    date_from = fields.Date()
    date_to = fields.Date()

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
            .replace("null::integer as amount", "al.released_amount as amount")
        )
        select_budget_query[0] = budget_query
        select_budget_query[
            10
        ] = """
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
                join budget_allocation_line al on al.fund_id = sf.id
                join account_analytic_account aa
                on aa.id = al.analytic_account_id
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
        statement_query = (
            select_statement[0]
            .replace(
                "null::integer as fund_id,",
                "a.fund_id as fund_id,",
            )
            .replace(
                "null::integer as fund_group_id,",
                "a.fund_group_id as fund_group_id,",
            )
        )
        select_statement[0] = statement_query
        select_statement[
            10
        ] = """
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
