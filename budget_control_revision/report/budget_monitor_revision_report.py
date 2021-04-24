# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetMonitorRevisionReport(models.Model):
    _name = "budget.monitor.revision.report"
    _description = "Budget Revision Monitoring Report"
    _auto = False
    _order = "date desc"
    _rec_name = "reference"

    reference = fields.Char()
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
    )
    date = fields.Date()
    amount = fields.Float()
    amount_type = fields.Selection(
        selection=[("1_budget", "Budget"), ("8_actual", "Actual")],
        string="Type",
    )
    revision_number = fields.Char()

    def _find_operating_unit(self):
        operating_unit_ids = self.env.user.operating_unit_ids
        if len(operating_unit_ids) == 1:
            ou = "= {}".format(operating_unit_ids.id)
        else:
            ou = "in {}".format(tuple(operating_unit_ids.ids))
        domain_operating_unit = "and bc.operating_unit_id {}".format(ou)
        return domain_operating_unit

    @property
    def _table_query(self):
        return "{}".format(self._get_sql())

    def _select_budget(self):
        return {
            0: """
            1000000000 + a.id as id,
            a.analytic_account_id,
            a.date_from as date,  -- approx date
            '1_budget' as amount_type,
            a.amount as amount,
            bc.name as reference,
            'Version ' || bc.revision_number::char as revision_number
        """
        }

    def _from_budget(self):
        return """
            from mis_budget_item a
            left outer join budget_control bc on a.budget_control_id = bc.id
        """

    def _where_budget(self):
        """
        Maybe function _find_operating_unit should be move on
        new module budget_control_revision_operating_unit
        """
        operating_unit = self._find_operating_unit()
        return """
            where a.state != 'draft' {}
        """.format(
            operating_unit
        )

    def _get_sql(self):
        select_budget_query = self._select_budget()
        key_select_budget_list = sorted(select_budget_query.keys())
        select_budget = ", ".join(
            select_budget_query[x] for x in key_select_budget_list
        )
        return "select {} {} {}".format(
            select_budget,
            self._from_budget(),
            self._where_budget(),
        )
