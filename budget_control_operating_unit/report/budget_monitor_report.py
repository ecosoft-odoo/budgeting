# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools import SQL


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    operating_unit_id = fields.Many2one(comodel_name="operating.unit")

    # Budget
    def _select_budget(self):
        select_budget_query = super()._select_budget()
        select_budget_query[30] = "b.operating_unit_id"
        return select_budget_query

    @api.model
    def _from_budget(self) -> SQL:
        return SQL("%s, b.operating_unit_id", super()._from_budget())

    @api.model
    def _get_where_budget(self):
        """
        Budget Manager or Access All OU -> show all OU
        else -> show only OU where user is located
        """
        where_budget = super()._get_where_budget()
        budget_manager = self.env.user.has_group(
            "budget_control.group_budget_control_manager"
        )
        access_all_ou = self.env.context.get("force_all_ou", False)
        if budget_manager or access_all_ou:
            return where_budget

        access_ou = self.env.user.operating_unit_ids

        ou_clause = (
            f"= {access_ou.id}" if len(access_ou) == 1 else f"IN {tuple(access_ou.ids)}"
        )
        domain_operating_unit = (
            f"AND (b.operating_unit_id {ou_clause} OR b.operating_unit_id IS NULL)"
        )
        where_budget = " ".join([where_budget, domain_operating_unit])
        return where_budget

    # All consumed
    def _select_statement(self, amount_type):
        select_statement = super()._select_statement(amount_type)
        select_statement[30] = "a.operating_unit_id"
        return select_statement
