# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetMonitorReport(models.Model):
    _name = "budget.monitor.report"
    _description = "Budget Monitoring Report"
    _auto = False
    _order = "date desc"
    _rec_name = "reference"

    res_id = fields.Reference(
        selection=lambda self: [("budget.control.line", "Budget Control Lines")]
        + self._get_budget_docline_model(),
        string="Resource ID",
    )
    kpi_id = fields.Many2one(
        comodel_name="budget.kpi",
        string="KPI",
    )
    source_document = fields.Char()
    reference = fields.Char()
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
    )
    analytic_group = fields.Many2one(
        comodel_name="account.analytic.group",
    )
    date = fields.Date()
    amount = fields.Float()
    amount_type = fields.Selection(
        selection=lambda self: [("10_budget", "Budget")]
        + self._get_budget_amount_type(),
        string="Type",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
    )
    account_id = fields.Many2one(
        comodel_name="account.account",
    )
    budget_period_id = fields.Many2one(
        comodel_name="budget.period",
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
    active = fields.Boolean()

    @property
    def _table_query(self):
        return """
            select a.*, p.id as budget_period_id
            from ({}) a
            left outer join date_range d
                on a.date between d.date_start and d.date_end
            left outer join budget_period p
                on a.date between p.bm_date_from and p.bm_date_to
            {}
        """.format(
            self._get_sql(), self._get_where_clause()
        )

    def _get_consumed_sources(self):
        return [
            {
                "model": ("account.move.line", "Account Move Line"),
                "type": ("80_actual", "Actual"),
                "budget_move": ("account_budget_move", "move_line_id"),
                "source_doc": ("account_move", "move_id"),
            }
        ]

    def _get_budget_docline_model(self):
        """Return list of all res_id models selection"""
        return [x["model"] for x in self._get_consumed_sources()]

    def _get_budget_amount_type(self):
        """Return list of all amount_type selection"""
        return [x["type"] for x in self._get_consumed_sources()]

    def _get_select_amount_types(self):
        sql_select = {}
        for source in self._get_consumed_sources():
            res_model = source["model"][0]  # i.e., account.move.line
            amount_type = source["type"][0]  # i.e., 80_actual
            res_field = source["budget_move"][1]  # i.e., move_line_id
            sql_select[amount_type] = {
                0: """
                %s000000000 + a.id as id,
                '%s,' || a.%s as res_id,
                a.kpi_id,
                a.analytic_account_id,
                a.analytic_group,
                a.date as date,
                '%s' as amount_type,
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
                % (amount_type[:2], res_model, res_field, amount_type)
            }
        return sql_select

    def _get_from_amount_types(self):
        sql_from = {}
        for source in self._get_consumed_sources():
            budget_table = source["budget_move"][0]  # i.e., account_budget_move
            doc_table = source["source_doc"][0]  # i.e., account_move
            doc_field = source["source_doc"][1]  # i.e., move_id
            amount_type = source["type"][0]  # i.e., 80_actual
            sql_from[
                amount_type
            ] = """
                from {} a
                left outer join {} b on a.{} = b.id
                left outer join res_company c on b.company_id = c.id
            """.format(
                budget_table,
                doc_table,
                doc_field,
            )
        return sql_from

    def _select_budget(self):
        return {
            0: """
            1000000000 + a.id as id,
            'budget.control.line,' || a.id as res_id,
            a.kpi_id,
            a.analytic_account_id,
            b.analytic_group,
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

    def _from_budget(self):
        return """
            from budget_control_line a
            join budget_control b
                on a.budget_control_id = b.id
            left join budget_control_company_rel c
                on b.id = c.budget_control_id
            left join res_company d on d.id = c.company_id
        """

    def _where_budget(self):
        visible_company = self.env.context.get("allowed_company_ids")
        if not visible_company:
            return "where b.active = true"

        if len(visible_company) > 1:
            companies = tuple(visible_company)
        else:
            companies = "({})".format(tuple(visible_company)[0])
        return "where b.active = true and (c.company_id in {} or c.company_id is null)".format(
            companies
        )

    def _groupby_budget(self):
        return """
            group by
                a.id,
                a.kpi_id,
                a.analytic_account_id,
                b.analytic_group,
                a.date_to,
                a.amount,
                b.name,
                b.state,
                a.active
        """

    def _select_statement(self, amount_type):
        return self._get_select_amount_types()[amount_type]

    def _from_statement(self, amount_type):
        return self._get_from_amount_types()[amount_type]

    def _where_actual(self):
        visible_company = self.env.context.get("allowed_company_ids")
        if not visible_company:
            return ""

        if len(visible_company) > 1:
            companies = tuple(visible_company)
        else:
            companies = "({})".format(tuple(visible_company)[0])
        return "where a.company_id in {}".format(companies)

    def _get_sql(self):
        select_budget_query = self._select_budget()
        key_select_budget_list = sorted(select_budget_query.keys())
        select_budget = ", ".join(
            select_budget_query[x] for x in key_select_budget_list
        )
        select_actual_query = self._select_statement("80_actual")
        key_select_actual_list = sorted(select_budget_query.keys())
        select_actual = ", ".join(
            select_actual_query[x] for x in key_select_actual_list
        )
        return "(select {} {} {} {}) union (select {} {} {})".format(
            select_budget,
            self._from_budget(),
            self._where_budget(),
            self._groupby_budget(),
            select_actual,
            self._from_statement("80_actual"),
            self._where_actual(),
        )

    def _get_where_clause(self):
        return "where d.type_id = p.plan_date_range_type_id"
