# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class SourceFundMonitorReport(models.Model):
    _name = "source.fund.monitor.report"
    _description = "Source Fund Monitoring Report"
    _auto = False
    _order = "fund_id desc"

    res_id = fields.Reference(
        selection=lambda self: [("budget.source.fund", "Budget Source Fund")]
        + self._get_budget_docline_model(),
        string="Resource ID",
    )
    reference = fields.Char()
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
    )
    fund_id = fields.Many2one(comodel_name="budget.source.fund")
    fund_group_id = fields.Many2one(comodel_name="budget.source.fund.group")
    amount = fields.Float()
    amount_type = fields.Selection(
        selection=lambda self: [("1_budget", "Budget")]
        + self._get_budget_amount_type(),
        string="Type",
    )

    @property
    def _table_query(self):
        return """select a.* from ({}) a""".format(self._get_sql())

    def _get_consumed_sources(self):
        return [
            {
                "model": ("account.move.line", "Account Move Line"),
                "type": ("8_actual", "Actual"),
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
            amount_type = source["type"][0]  # i.e., 8_actual
            res_field = source["budget_move"][1]  # i.e., move_line_id
            sql_select[amount_type] = {
                0: """
                %s000000000 + a.id as id,
                '%s,' || a.%s as res_id,
                a.reference as reference,
                a.fund_id as fund_id,
                a.fund_group_id as fund_group_id,
                a.analytic_account_id,
                '%s' as amount_type,
                a.credit-a.debit as amount
                """
                % (amount_type[:1], res_model, res_field, amount_type)
            }
        return sql_select

    def _get_from_amount_types(self):
        sql_from = {}
        for source in self._get_consumed_sources():
            budget_table = source["budget_move"][0]  # i.e., account_budget_move
            doc_table = source["source_doc"][0]  # i.e., account_move
            doc_field = source["source_doc"][1]  # i.e., move_id
            amount_type = source["type"][0]  # i.e., 8_actual
            sql_from[
                amount_type
            ] = """
                from {} a
                left outer join {} b on a.{} = b.id
            """.format(
                budget_table,
                doc_table,
                doc_field,
            )
        return sql_from

    def _select_budget(self):
        return {
            0: """
            1000000000 + sf.id as id,
            'budget.source.fund,' || sf.id as res_id,
            sf.name as reference,
            sf.id as fund_id,
            sf_group.id as fund_group_id,
            null::integer as analytic_account_id,
            '1_budget' as amount_type,
            null::integer as amount
        """
        }

    def _from_budget(self):
        return """
            from budget_source_fund sf
            join budget_source_fund_group sf_group
            on sf_group.id = sf.fund_group_id
        """

    def _where_budget(self):
        return """ where sf.active is true """

    def _select_statement(self, amount_type):
        return self._get_select_amount_types()[amount_type]

    def _from_statement(self, amount_type):
        return self._get_from_amount_types()[amount_type]

    def _where_actual(self):
        return """
            where b.state = 'posted'
        """

    def _get_sql(self):
        select_budget_query = self._select_budget()
        key_select_budget_list = sorted(select_budget_query.keys())
        select_budget = ", ".join(
            select_budget_query[x] for x in key_select_budget_list
        )
        select_actual_query = self._select_statement("8_actual")
        key_select_actual_list = sorted(select_budget_query.keys())
        select_actual = ", ".join(
            select_actual_query[x] for x in key_select_actual_list
        )
        return "(select {} {} {}) union (select {} {} {})".format(
            select_budget,
            self._from_budget(),
            self._where_budget(),
            select_actual,
            self._from_statement("8_actual"),
            self._where_actual(),
        )
