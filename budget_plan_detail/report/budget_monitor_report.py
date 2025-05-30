# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    # Budget
    def _select_budget(self):
        select_budget_query = super()._select_budget()
        # Find analytic tag dimension (if any)
        dimension_fields = self._get_dimension_fields("budget.plan.line.detail")
        formatted_dimension_fields = ""
        if dimension_fields:
            formatted_dimension_fields = ", " + ", ".join(
                f"null::integer as {f}" for f in dimension_fields
            )
        select_budget_query[80] = (
            f"null::integer as fund_id, "
            f"null::integer as fund_group_id {formatted_dimension_fields}"
        )
        return select_budget_query

    # All consumed
    def _select_statement(self, amount_type):
        select_statement = super()._select_statement(amount_type)

        # Find analytic tag dimension (from budget plan line detail)
        budget_dimension_fields = self._get_dimension_fields("budget.plan.line.detail")
        formatted_dimension_fields = ""

        # Find analytic tag dimension (from each budget_move)
        parts = self._get_from_amount_types()[amount_type].split()
        if parts[0].upper() == "FROM" and parts[2] == "a":
            table_name = parts[1].replace("_", ".")
            dimension_fields = self._get_dimension_fields(table_name)
            if dimension_fields:
                formatted_dimension_fields = ", " + ", ".join(
                    f"a.{f} as {f}" for f in dimension_fields
                )

        # For case: not installed budget_plan_detail_* but install budget_control_*
        if budget_dimension_fields and not formatted_dimension_fields:
            formatted_dimension_fields = ", " + ", ".join(
                f"null::integer as {f}" for f in budget_dimension_fields
            )
        select_statement[80] = (
            f"a.fund_id, a.fund_group_id {formatted_dimension_fields}"
        )
        return select_statement
