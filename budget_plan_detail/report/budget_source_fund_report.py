# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools import SQL


class SourceFundMonitorReport(models.Model):
    _name = "budget.source.fund.report"
    _inherit = "budget.common.monitoring"
    _description = "Budget Source Fund Monitoring Report"
    _auto = False
    _order = "fund_id desc"

    date_from = fields.Date()
    date_to = fields.Date()

    @property
    def _table_query(self) -> SQL:
        return SQL("%s %s %s", self._select(), self._from(), self._where())

    @api.model
    def _select(self) -> SQL:
        return SQL(
            """SELECT a.*, p.id AS budget_period_id""",
        )

    @api.model
    def _from(self) -> SQL:
        return SQL(
            """
            FROM (%(table)s) a
            LEFT JOIN budget_period p
                ON a.date_to between p.bm_date_from AND p.bm_date_to
            LEFT JOIN date_range d ON a.date_to between d.date_start AND d.date_end
                AND d.type_id = p.plan_date_range_type_id
            """,
            table=self._get_sql(),
        )

    @api.model
    def _where(self) -> SQL:
        return SQL("")

    def _get_select_amount_types(self):
        sql_select = {}
        formatted_dimension_fields = ""
        budget_dimension_fields = self._get_dimension_fields("budget.plan.line.detail")

        for source in self._get_consumed_sources():
            res_model = source["model"][0]  # i.e., account.move.line
            amount_type = source["type"][0]  # i.e., 80_actual
            res_field = source["budget_move"][1]  # i.e., move_line_id
            budget_table = source["budget_move"][0]  # i.e., account_budget_move
            table_model = budget_table.replace("_", ".")

            # Find analytic tag dimension (if any)
            dimension_fields = self._get_dimension_fields(table_model)
            if dimension_fields:
                formatted_dimension_fields = ", " + ", ".join(
                    f"a.{f} as {f}" for f in dimension_fields
                )
            elif budget_dimension_fields:
                formatted_dimension_fields = ", " + ", ".join(
                    f"null::integer as {f}" for f in budget_dimension_fields
                )
            else:
                formatted_dimension_fields = ""

            sql_select[amount_type] = {
                0: f"""
                {amount_type[:2]}000000000 + a.id as id,
                '{res_model},' || a.{res_field} as res_id,
                a.reference as reference,
                a.fund_id as fund_id,
                a.fund_group_id as fund_group_id,
                a.analytic_account_id,
                '{amount_type}' as amount_type,
                a.credit-a.debit as amount,
                -- change aa.bm_date_from, aa.bm_date_to to a.date
                a.date as date_from,
                a.date as date_to,
                1::boolean as plan_active,
                1::boolean as active {formatted_dimension_fields}
                """
            }
        return sql_select

    def _get_from_amount_types(self):
        sql_from = {}
        for source in self._get_consumed_sources():
            budget_table = source["budget_move"][0]  # i.e., account_budget_move
            amount_type = source["type"][0]  # i.e., 80_actual
            sql_from[amount_type] = f"""
                FROM {budget_table} a
                JOIN account_analytic_account aa
                    ON aa.id = a.analytic_account_id
            """
        return sql_from

    def _select_budget(self):
        dimension_fields = self._get_dimension_fields("budget.plan.line.detail")
        # Find analytic tag dimension (if any)
        formatted_dimension_fields = ""
        if dimension_fields:
            formatted_dimension_fields = ", " + ", ".join(
                f"pl_detail.{x} as {x}" for x in dimension_fields
            )

        return {
            0: f"""
            1000000000 + pl_detail.id as id,
            'budget.source.fund,' || sf.id as res_id,
            sf.name as reference,
            sf.id as fund_id,
            sf_group.id as fund_group_id,
            aa.id as analytic_account_id,
            '10_budget' as amount_type,
            pl_detail.released_amount as amount,
            bp.bm_date_from as date_from,
            bp.bm_date_to as date_to,
            -- make sure source fund report will show only allocation active
            plan.active as plan_active,
            bc.active as active {formatted_dimension_fields}
        """
        }

    @api.model
    def _from_budget(self) -> SQL:
        return SQL(
            """
            FROM budget_source_fund sf
            JOIN budget_source_fund_group sf_group
                ON sf_group.id = sf.fund_group_id
            JOIN budget_plan_line_detail pl_detail ON pl_detail.fund_id = sf.id
            JOIN budget_plan plan ON plan.id = pl_detail.plan_id
            JOIN account_analytic_account aa
                ON aa.id = pl_detail.analytic_account_id
            JOIN budget_control bc
                ON bc.analytic_account_id = aa.id
            JOIN budget_period bp
                ON bc.budget_period_id = bp.id
            WHERE sf.active = TRUE AND plan.active = TRUE AND bc.active = TRUE
            """,
        )

    def _select_statement(self, amount_type):
        return self._get_select_amount_types()[amount_type]

    @api.model
    def _from_statement(self, amount_type) -> SQL:
        return SQL(self._get_from_amount_types()[amount_type])

    @api.model
    def _where_actual(self) -> SQL:
        return SQL("")

    @api.model
    def _get_sql(self) -> SQL:
        # budget
        select_budget_query = self._select_budget()
        key_select_budget_list = sorted(select_budget_query.keys())
        select_budget = ", ".join(
            select_budget_query[x] for x in key_select_budget_list
        )
        # commitment
        select_actual_query = self._select_statement("80_actual")
        key_select_actual_list = sorted(select_budget_query.keys())
        select_actual = ", ".join(
            select_actual_query[x] for x in key_select_actual_list
        )
        return SQL(
            """
            (SELECT %(select_budget)s %(from_budget)s)
            UNION ALL
            (SELECT %(select_actual)s %(from_actual)s %(where_actual)s)
            """,
            select_budget=SQL(select_budget),
            from_budget=self._from_budget(),
            select_actual=SQL(select_actual),
            from_actual=self._from_statement("80_actual"),
            where_actual=self._where_actual(),
        )
