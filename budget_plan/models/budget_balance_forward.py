# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetBalanceForward(models.Model):
    _inherit = "budget.balance.forward"

    def _invalidate_forward_budget_records(self):
        """Plan totals include the forward balance of their period."""
        res = super()._invalidate_forward_budget_records()
        lines = self.mapped("forward_line_ids")
        if not lines:
            return res
        target_analytics = lines.mapped("to_analytic_account_id") + lines.mapped(
            "accumulate_analytic_account_id"
        )
        target_periods = self.mapped("to_budget_period_id")
        plan_lines = (
            self.env["budget.plan.line"]
            .sudo()
            .search(
                [
                    ("budget_period_id", "in", target_periods.ids),
                    ("analytic_account_id", "in", target_analytics.ids),
                ]
            )
        )
        plan_lines.invalidate_recordset(
            ["amount_forward_in", "allocated_amount", "amount_unallocated"]
        )
        plan_lines.mapped("plan_id").invalidate_recordset(["total_amount"])
        return res

    def _check_can_cancel(self):
        """A confirmed plan of the target period has taken the forward balance."""
        Plan = self.env["budget.plan"].sudo()
        for rec in self:
            target_analytics = rec.forward_line_ids.mapped(
                "to_analytic_account_id"
            ) + rec.forward_line_ids.mapped("accumulate_analytic_account_id")
            if target_analytics and Plan.search_count(
                [
                    ("budget_period_id", "=", rec.to_budget_period_id.id),
                    ("line_ids.analytic_account_id", "in", target_analytics.ids),
                    ("state", "in", ["confirm", "done"]),
                ],
                limit=1,
            ):
                rec._raise_target_budget_started()
        return super()._check_can_cancel()
