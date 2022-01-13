# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SourceFundMonitorReport(models.Model):
    _inherit = "source.fund.monitor.report"

    date_from = fields.Date()
    date_to = fields.Date()
    active = fields.Boolean()
    budget_period_id = fields.Many2one(comodel_name="budget.period")

    @property
    def _table_query(self):
        return """
            select a.*, d.id as date_range_id, p.id as budget_period_id
            from ({}) a {} {}
        """.format(
            self._get_sql(), self._get_join_sql(), self._get_where_sql()
        )

    def _get_join_sql(self):
        join_sql = super()._get_join_sql()
        new_join_sql = """
        left outer join date_range d
            on a.date_to between d.date_start and d.date_end
        left outer join budget_period p
            on a.date_to between p.bm_date_from and p.bm_date_to
        """
        join_sql = "\n".join([join_sql, new_join_sql])
        return join_sql

    # Budget
    def _select_budget(self):
        select_budget_query = super()._select_budget()
        # Replace null analytic and amount
        budget_query = (
            select_budget_query[0]
            .replace("1000000000 + sf.id as id", "1000000000 + al.id as id")
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
            al.date_from as date_from,
            al.date_to as date_to,
            bc.active as active
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

    # All consumed
    def _select_statement(self, amount_type):
        select_statement = super()._select_statement(amount_type)
        select_statement[
            10
        ] = """
            aa.bm_date_from as date_from,
            aa.bm_date_to as date_to,
            1::boolean as active
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
