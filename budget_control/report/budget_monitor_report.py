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
        selection=[
            ("mis.budget.item", "Budget Item"),
            ("account.move.line", "Account Move Line"),
        ],
        string="Resource ID",
    )
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
        selection=[("1_budget", "Budget"), ("8_actual", "Actual")],
        string="Type",
    )
    account_id = fields.Many2one(
        comodel_name="account.account",
    )

    @property
    def _table_query(self):
        return "%s" % (self._get_sql())

    def _select_budget(self):
        return [
            """
            1000000000 + mbi.id as id,
            'mis.budget.item,' || mbi.id as res_id,
            mbi.analytic_account_id,
            bc.analytic_group,
            mbi.date_from as date,  -- approx date
            '1_budget' as amount_type,
            mbi.amount as amount,
            null::integer as account_id,
            bc.name as reference
        """
        ]

    def _from_budget(self):
        return """
            from mis_budget_item mbi
            left outer join budget_control bc on mbi.budget_control_id = bc.id
        """

    def _where_budget(self):
        return """
            -- where mbi.active = true and mbi.state = 'done'
            where mbi.active = true
        """

    def _select_actual(self):
        return [
            """
            8000000000 + a.id as id,
            'account.move.line,' || a.move_line_id as res_id,
            a.analytic_account_id,
            a.analytic_group,
            a.date as date,
            '8_actual' as amount_type,
            a.credit-a.debit as amount,
            a.account_id,
            b.name as reference
        """
        ]

    def _from_actual(self):
        return """
            from account_budget_move a
            left outer join account_move b on a.move_id = b.id
        """

    def _where_actual(self):
        return """
            where b.state = 'posted' and b.not_affect_budget is null
        """

    def _get_sql(self):
        select_budget_query = self._select_budget()
        select_budget = ", ".join(sorted(select_budget_query))
        select_actual_query = self._select_actual()
        select_actual = ", ".join(sorted(select_actual_query))
        return "(select {} {} {}) union (select {} {} {})".format(
            select_budget,
            self._from_budget(),
            self._where_budget(),
            select_actual,
            self._from_actual(),
            self._where_actual(),
        )
