# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    operating_unit_id = fields.Many2one(comodel_name="operating.unit")

    def _get_group_access_all_ou(self):
        """Hook this function for add group access all ou"""
        return self.env.user.has_group("budget_control.group_budget_control_manager")

    def _get_where_clause(self):
        """Show monitoring according to the operating unit where the user is located,
        except for budget managers and user with the right to see everything"""
        where_clause = super()._get_where_clause()
        operating_unit_ids = self.env.user.operating_unit_ids
        group_access_all_ou = self._get_group_access_all_ou()
        if group_access_all_ou or self._context.get("force_all_ou", False):
            operating_unit_ids = self.env["operating.unit"].sudo().search([])
        if not operating_unit_ids:
            return where_clause
        ou_clause = (
            "= {}".format(operating_unit_ids.id)
            if len(operating_unit_ids) == 1
            else "IN {}".format(tuple(operating_unit_ids.ids))
        )
        domain_operating_unit = (
            "AND (a.operating_unit_id {} OR a.operating_unit_id IS NULL)".format(
                ou_clause
            )
        )
        where_clause = " ".join([where_clause, domain_operating_unit])
        return where_clause

    # Budget
    def _select_budget(self):
        select_budget_query = super()._select_budget()
        select_budget_query[30] = "b.operating_unit_id"
        return select_budget_query

    # All consumed
    def _select_statement(self, amount_type):
        select_statement = super()._select_statement(amount_type)
        select_statement[30] = "a.operating_unit_id"
        return select_statement
