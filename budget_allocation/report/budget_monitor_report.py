# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    fund_id = fields.Many2one(comodel_name="budget.source.fund", string="Fund")
    fund_group_id = fields.Many2one(
        comodel_name="budget.source.fund.group", string="Fund Group"
    )

    def _get_dimension_fields(self):
        if self.env.context.get("update_custom_fields"):
            return []  # Avoid to report these columns when not yet created
        return [
            x
            for x in self.env["budget.allocation.line"].fields_get().keys()
            if x.startswith("x_dimension_")
        ]

    # Budget
    def _select_budget(self):
        select_budget_query = super()._select_budget()
        # Find analytic tag dimension (if any)
        dimension_fields = self._get_dimension_fields()
        formatted_dimension_fields = ""
        if dimension_fields:
            dimension_fields = [f"null::integer as {x}" for x in dimension_fields]
            if len(dimension_fields) == 1:
                formatted_dimension_fields = f", {dimension_fields[0]}"
            else:
                formatted_dimension_fields = ", ".join(dimension_fields)
                formatted_dimension_fields = f", {formatted_dimension_fields}"
        select_budget_query[
            80
        ] = "null::integer as fund_id, null::integer as fund_group_id {}".format(
            formatted_dimension_fields
        )
        return select_budget_query

    # All consumed
    def _select_statement(self, amount_type):
        select_statement = super()._select_statement(amount_type)
        # Find analytic tag dimension (if any)
        dimension_fields = self._get_dimension_fields()
        formatted_dimension_fields = ""
        if dimension_fields:
            dimension_fields = [f"a.{x} as {x}" for x in dimension_fields]
            if len(dimension_fields) == 1:
                formatted_dimension_fields = f", {dimension_fields[0]}"
            else:
                formatted_dimension_fields = ", ".join(dimension_fields)
                formatted_dimension_fields = f", {formatted_dimension_fields}"
        select_statement[80] = "a.fund_id, a.fund_group_id {}".format(
            formatted_dimension_fields
        )
        return select_statement
