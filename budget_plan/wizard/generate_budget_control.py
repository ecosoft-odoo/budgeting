# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class GenerateBudgetControl(models.TransientModel):
    _inherit = "generate.budget.control"

    budget_plan_id = fields.Many2one(
        comodel_name="budget.plan",
        default=lambda self: self._get_budget_plan_id(),
    )

    @api.onchange("all_analytic_accounts", "analytic_group_ids")
    def _onchange_analytic_accounts(self):
        if self._context.get("active_model") != "budget.plan":
            return super()._onchange_analytic_accounts()

    @api.model
    def _get_budget_plan_id(self):
        model = self._context.get("active_model")
        budget_plan = False
        if model == "budget.plan":
            budget_plan = self.env["budget.plan"].browse(
                self._context.get("active_id")
            )
        return budget_plan

    @api.model
    def _get_budget_period_id(self):
        model = self._context.get("active_model")
        if model == "budget.plan":
            budget_plan = self._get_budget_plan_id()
            return budget_plan.budget_period_id
        return super()._get_budget_period_id()

    def _update_budget_control_allocation(self, budget_controls, analytics):
        BudgetAllocation = self.env["budget.source.fund.allocation"]
        allocations = BudgetAllocation.search(
            [
                ("analytic_account_id", "in", analytics.ids),
                ("budget_period_id", "=", self.budget_period_id.id),
                ("amount", ">", 0.0),
            ]
        )
        for bc in budget_controls:
            for allocation in allocations:
                if bc.analytic_account_id == allocation.analytic_account_id:
                    allocation.write({"budget_control_id": bc.id})
        return allocations

    def _prepare_value_duplicate_plan(self, vals):
        plan_date_range_id = self.budget_period_id.plan_date_range_type_id.id
        budget_id = self.budget_id.id
        budget_name = self.budget_period_id.name
        plan_id = self.budget_plan_id.id
        return map(
            lambda l: {
                "name": "{} :: {}".format(
                    budget_name, l["analytic_account_id"].name
                ),
                "budget_id": budget_id,
                "analytic_account_id": l["analytic_account_id"].id,
                "plan_date_range_type_id": plan_date_range_id,
                "plan_id": plan_id,
            },
            vals,
        )

    def _prepare_value_duplicate(self, vals):
        model = self._context.get("active_model")
        if model == "budget.plan":
            res = self._prepare_value_duplicate_plan(vals)
        else:
            res = super()._prepare_value_duplicate(vals)
        return res

    def _hook_budget_controls(self, budget_controls):
        budget_controls = super()._hook_budget_controls(budget_controls)
        analytics = budget_controls.mapped("analytic_account_id")
        self._update_budget_control_allocation(budget_controls, analytics)
        return budget_controls

    def _hook_existing_analytics(self, existing_analytics):
        existing_analytics = super()._hook_existing_analytics(
            existing_analytics
        )
        BudgetControl = self.env["budget.control"]
        budget_controls = BudgetControl.search(
            [
                ("analytic_account_id", "in", existing_analytics.ids),
                ("budget_id", "=", self.budget_id.id),
            ]
        )
        self._update_budget_control_allocation(
            budget_controls, existing_analytics
        )
        return existing_analytics
