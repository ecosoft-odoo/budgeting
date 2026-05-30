# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    # Budget
    def _select_budget(self):
        select_budget_query = super()._select_budget()
        # Canonical dimension set: budget.plan.line.detail always holds them all.
        # Sort so every UNION branch emits dimensions in the same order.
        dimension_fields = sorted(self._get_dimension_fields("budget.plan.line.detail"))
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

        # Canonical, ordered dimension set (reference = budget.plan.line.detail).
        # Every branch must emit exactly these columns in the same order so the
        # UNION column count and positions line up. A given budget_move may hold
        # only a subset of the dimensions (e.g. created before its model
        # existed); emit a.<field> when present, null otherwise.
        dimension_fields = sorted(self._get_dimension_fields("budget.plan.line.detail"))
        formatted_dimension_fields = ""
        if dimension_fields:
            source_fields = set()
            parts = self._get_from_amount_types()[amount_type].split()
            if parts[0].upper() == "FROM" and parts[2] == "a":
                table_name = parts[1].replace("_", ".")
                source_fields = set(self._get_dimension_fields(table_name))
            formatted_dimension_fields = ", " + ", ".join(
                (f"a.{f}" if f in source_fields else "null::integer") + f" as {f}"
                for f in dimension_fields
            )
        select_statement[80] = (
            f"a.fund_id, a.fund_group_id {formatted_dimension_fields}"
        )
        return select_statement
