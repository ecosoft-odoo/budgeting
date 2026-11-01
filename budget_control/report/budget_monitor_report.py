# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re

from odoo import api, fields, models
from odoo.tools import SQL


class BudgetMonitorReport(models.Model):
    _name = "budget.monitor.report"
    _inherit = "budget.common.monitoring"
    _description = "Budget Monitoring Report"
    _auto = False
    _order = "date desc"
    _rec_name = "reference"

    kpi_id = fields.Many2one(
        comodel_name="budget.kpi",
        string="KPI",
    )
    source_document = fields.Char()
    analytic_plan = fields.Many2one(
        comodel_name="account.analytic.plan",
    )
    date = fields.Date()
    product_id = fields.Many2one(
        comodel_name="product.product",
    )
    account_id = fields.Many2one(
        comodel_name="account.account",
    )
    budget_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submit", "Submitted"),
            ("done", "Controlled"),
            ("cancel", "Cancelled"),
        ],
    )
    fwd_commit = fields.Boolean()
    companies = fields.Char()

    @property
    def _table_sql(self) -> SQL:
        return SQL("(%s %s %s)", self._select(), self._from(), self._where())

    @api.model
    def _select(self) -> SQL:
        return SQL(
            """SELECT a.*, COALESCE(own_period.id, fiscal_period.id)
                AS budget_period_id""",
        )

    @api.model
    def _from(self) -> SQL:
        return SQL(
            """
            FROM (%(table)s) a
            LEFT JOIN account_analytic_account analytic
                ON analytic.id = a.analytic_account_id
            -- Budget and forward rows know their period, a lifetime
            -- analytic has its own
            LEFT JOIN budget_period own_period
                ON own_period.id = COALESCE(
                    a.source_period_id,
                    CASE WHEN analytic.budget_control_scope = 'lifetime'
                        THEN analytic.budget_period_id END
                )
                AND (
                    a.source_period_id IS NOT NULL
                    OR a.date BETWEEN own_period.bm_date_from
                        AND own_period.bm_date_to
                )
            -- Other rows take the fiscal period of their date: the period of
            -- the document company, or of a parent
            LEFT JOIN res_company source_company
                ON source_company.id = a.source_company_id
            LEFT JOIN (
                SELECT period.id, period.bm_date_from, period.bm_date_to,
                    array_agg(pc.company_id) FILTER (
                        WHERE pc.company_id IS NOT NULL
                    ) AS company_ids
                FROM budget_period period
                LEFT JOIN budget_period_company_rel pc
                    ON pc.budget_period_id = period.id
                WHERE period.budget_scope = 'fiscal'
                GROUP BY period.id
            ) fiscal_period
                ON a.source_period_id IS NULL
                AND COALESCE(analytic.budget_control_scope, 'fiscal') = 'fiscal'
                AND a.date BETWEEN fiscal_period.bm_date_from
                    AND fiscal_period.bm_date_to
                AND (
                    fiscal_period.company_ids IS NULL
                    OR fiscal_period.company_ids && string_to_array(
                        rtrim(source_company.parent_path, '/'), '/'
                    )::integer[]
                )
            """,
            table=self._get_sql(),
        )

    @api.model
    def _where(self) -> SQL:
        return SQL("")

    @api.model
    def _get_consumed_sql(self, amount_type, where=None) -> SQL:
        """UNION branch of the budget moves of ``amount_type``, a source of
        ``_get_consumed_sources()``, filtered by ``where``."""
        select = self._select_statement(amount_type)
        return SQL(
            "(SELECT %s %s %s)",
            SQL(", ".join(select[key] for key in sorted(select))),
            self._from_statement(amount_type),
            where or SQL(""),
        )

    @api.model
    def _get_sql_branches(self) -> list:
        """UNION ALL branches of the monitoring: budgets, actuals and forward
        balances. Extensions add theirs, e.g. the branch of a commitment
        source with ``_get_consumed_sql()``."""
        select_budget = self._select_budget()
        return [
            SQL(
                "(SELECT %s %s)",
                SQL(", ".join(select_budget[key] for key in sorted(select_budget))),
                self._from_budget(),
            ),
            self._get_consumed_sql("80_actual", self._where_actual()),
            SQL("(%s)", self._select_forward_balance()),
        ]

    @api.model
    def _get_sql(self) -> SQL:
        return SQL(" UNION ALL ").join(self._get_sql_branches())

    @api.model
    def _select_forward_balance(self) -> SQL:
        """Return only the source-period deduction for monitoring.

        The target matrix already includes Forward Balance, so exposing a
        positive Forward In movement would double-count it in pivot totals.
        Target composition remains available on Budget Plan and Budget Control.
        """
        companies = """
            (
                SELECT string_agg(company.name::text, ', ')
                FROM budget_balance_forward_company_rel forward_company
                INNER JOIN res_company company
                    ON company.id = forward_company.company_id
                WHERE forward_company.forward_id = forward.id
            )
        """
        source_document = """
            forward.name || ' (' || from_period.name || ' -> ' || to_period.name || ')'
        """
        extra_columns = self._select_forward_balance_extra()
        extra_select = ", ".join(extra_columns[key] for key in sorted(extra_columns))
        extra_select = f", {extra_select}" if extra_select else ""
        return SQL(
            f"""
            SELECT
                13000000000 + line.id AS id,
                'budget.balance.forward.line,' || line.id AS res_id,
                NULL::integer AS kpi_id,
                line.analytic_account_id AS analytic_account_id,
                source_analytic.plan_id AS analytic_plan,
                from_period.bm_date_to AS date,
                '12_forward_out' AS amount_type,
                -(line.amount_balance_forward + line.amount_balance_accumulate)
                    AS amount,
                NULL::integer AS product_id,
                NULL::integer AS account_id,
                forward.name AS reference,
                {source_document} AS source_document,
                NULL::char AS budget_state,
                FALSE AS fwd_commit,
                {companies} AS companies,
                TRUE AS active
                {extra_select}
            FROM budget_balance_forward_line line
            INNER JOIN budget_balance_forward forward ON forward.id = line.forward_id
            INNER JOIN budget_period from_period
                ON from_period.id = forward.from_budget_period_id
            INNER JOIN budget_period to_period
                ON to_period.id = forward.to_budget_period_id
            INNER JOIN account_analytic_account source_analytic
                ON source_analytic.id = line.analytic_account_id
            WHERE forward.state = 'done'
                AND (line.amount_balance_forward + line.amount_balance_accumulate) != 0
            """
        )

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        self.env["account.analytic.plan"]._patch_budget_plan_view(
            arch, view_type, self._name
        )
        return arch, view

    @api.model
    def _select_forward_balance_extra(self):
        """Hook for extension dimensions on every forward UNION branch."""
        select = {
            95: "forward.from_budget_period_id AS source_period_id, "
            "NULL::integer AS source_company_id"
        }
        if self._budget_plan_fnames():
            select[90] = self._select_plan_columns_null()
        return select

    def _budget_plan_fnames(self):
        """``x_plan<id>_id`` columns, one per root plan, in a fixed order."""
        return sorted(
            fname for fname in self._fields if re.fullmatch(r"x_plan\d+_id", fname)
        )

    def _select_plan_columns_null(self):
        """Budget and forward rows only know their budget analytic, which is
        never in a plan column."""
        return ", ".join(
            f"NULL::integer AS {fname}" for fname in self._budget_plan_fnames()
        )

    def _get_select_amount_types(self):
        sql_select = {}
        for source in self._get_consumed_sources():
            res_model = source["model"][0]  # i.e., account.move.line
            amount_type = source["type"][0]  # i.e., 80_actual
            res_field = source["budget_move"][1]  # i.e., move_line_id
            sql_select[amount_type] = {
                0: f"""
                {amount_type[:2]}000000000 + a.id as id,
                '{res_model},' || a.{res_field} as res_id,
                a.kpi_id,
                a.analytic_account_id,
                a.analytic_plan,
                a.date as date,
                '{amount_type}' as amount_type,
                a.credit-a.debit as amount,
                a.product_id,
                a.account_id,
                a.reference as reference,
                a.source_document as source_document,
                null::char as budget_state,
                a.fwd_commit,
                c.name::text AS companies,
                1::boolean as active
                """
            }
            sql_select[amount_type][95] = (
                "NULL::integer AS source_period_id, a.company_id AS source_company_id"
            )
            plan_fnames = self._budget_plan_fnames()
            if plan_fnames:
                move_fields = self._get_budget_move_fields(source["budget_move"][0])
                sql_select[amount_type][90] = ", ".join(
                    f"a.{fname}"
                    if fname in move_fields
                    else f"NULL::integer AS {fname}"
                    for fname in plan_fnames
                )
        return sql_select

    def _get_budget_move_fields(self, table):
        """Fields of the budget move model stored in ``table``."""
        return next(
            (
                model._fields
                for model in self.env.registry.values()
                if not model._abstract and model._table == table
            ),
            {},
        )

    def _get_from_amount_types(self):
        sql_from = {}
        for source in self._get_consumed_sources():
            budget_table = source["budget_move"][0]  # i.e., account_budget_move
            doc_table = source["source_doc"][0]  # i.e., account_move
            doc_field = source["source_doc"][1]  # i.e., move_id
            amount_type = source["type"][0]  # i.e., 80_actual
            sql_from[amount_type] = f"""
                FROM {budget_table} a
                LEFT OUTER JOIN {doc_table} b ON a.{doc_field} = b.id
                LEFT OUTER JOIN res_company c ON b.company_id = c.id
            """
        return sql_from

    def _select_budget(self):
        select = self._select_budget_base()
        select[95] = (
            "b.budget_period_id AS source_period_id, NULL::integer AS source_company_id"
        )
        if self._budget_plan_fnames():
            select[90] = self._select_plan_columns_null()
        return select

    def _select_budget_base(self):
        return {
            0: """
            10000000000 + a.id as id,
            'budget.control.line,' || a.id as res_id,
            a.kpi_id,
            a.analytic_account_id,
            b.analytic_plan,
            a.date_to as date,  -- approx date
            '10_budget' as amount_type,
            a.amount as amount,
            null::integer as product_id,
            null::integer as account_id,
            b.name as reference,
            null::char as source_document,
            b.state as budget_state,
            0::boolean as fwd_commit,
            string_agg(d.name::text, ', ') AS companies,
            a.active as active
        """
        }

    @api.model
    def _from_budget(self) -> SQL:
        return SQL(
            f"""
            FROM budget_control_line a
            INNER JOIN budget_control b ON a.budget_control_id = b.id
            LEFT JOIN budget_control_company_rel c
                ON b.id = c.budget_control_id
            LEFT JOIN res_company d ON d.id = c.company_id
            WHERE {self._get_where_budget()}
            GROUP BY
                a.id, a.kpi_id, a.analytic_account_id,
                b.analytic_plan, a.date_to, a.amount,
                b.name, b.state, a.active, b.budget_period_id
            """,
        )

    @api.model
    def _get_where_budget(self):
        """
        Hook this function for add where clause for budget
        use for module budget_control_operating_unit
        """
        return "b.active = TRUE AND b.state != 'cancel'"

    def _select_statement(self, amount_type):
        return self._get_select_amount_types()[amount_type]

    @api.model
    def _from_statement(self, amount_type) -> SQL:
        return SQL(self._get_from_amount_types()[amount_type])

    @api.model
    def _where_actual(self) -> SQL:
        return SQL("")
