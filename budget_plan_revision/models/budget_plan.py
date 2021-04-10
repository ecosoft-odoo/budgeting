# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ast

from odoo import api, fields, models


class BudgetPlan(models.Model):
    _name = "budget.plan"
    _inherit = ["budget.plan", "base.revision"]

    current_revision_id = fields.Many2one(
        comodel_name="budget.plan",
    )
    old_revision_ids = fields.One2many(
        comodel_name="budget.plan",
    )
    init_revision = fields.Boolean(
        string="Initial Version", default=True, readonly=True
    )
    revision_number = fields.Integer()
    enable_revision_number = fields.Boolean(
        compute="_compute_group_revision_number"
    )

    @api.depends("revision_number")
    def _compute_group_revision_number(self):
        group_enable_revision = self.env.user.has_group(
            "budget_plan_revision.group_enable_revision"
        )
        self.update({"enable_revision_number": group_enable_revision})
        return True

    def button_open_budget_control(self):
        # Beacuse we want to use revision number, and inactive should be shown
        action = super().button_open_budget_control()
        action["context"]["active_test"] = False
        return action

    def _get_context_wizard(self):
        ctx = super()._get_context_wizard()
        ctx.update({"revision": self.revision_number})
        return ctx

    def _hook_new_budget_plan(self, new_plan):
        """ Hooks for do something new plan """
        new_plan.init_revision = False
        return True

    def action_create_update_budget_control(self):
        self = self.with_context(active_test=False)
        return super().action_create_update_budget_control()

    def create_revision(self):
        """ Create budget plan revision and all its budget controls """
        self = self.sudo().with_context(active_test=False)
        res = super().create_revision()
        # Based on new budget_plan, create new budget controls by create_revision()
        new_plan = self.search(ast.literal_eval(res.get("domain", False)))
        new_plan.ensure_one()
        new_plan.active = True
        # By default, there should be no budget_controls, but in case there is,
        # so we want to make sure not to create it.
        new_plan.plan_line.invalidate_cache()
        no_bc_lines = new_plan.plan_line.filtered_domain(
            [("budget_control_ids", "=", False)]
        )
        analytics = no_bc_lines.mapped("analytic_account_id")
        # Find revisions of budget_controls, and use latest one to create_revision()
        budget_controls = self.env["budget.control"].search(
            [
                ("analytic_account_id", "in", analytics.ids),
                ("date_from", "<=", self.budget_period_id.bm_date_from),
                ("date_to", ">=", self.budget_period_id.bm_date_to),
            ]
        )
        for analytic in analytics:
            prev_control = budget_controls.filtered_domain(
                [("analytic_account_id", "=", analytic.id)]
            ).sorted("revision_number")[
                -1:
            ]  # sorted asc and get the last one
            if prev_control:
                prev_control.with_context(
                    revision_number=new_plan.revision_number
                ).create_revision()
        # Ensure all budget controls are set as active to start
        new_plan.invalidate_cache()
        new_plan.with_context(active_test=False).budget_control_ids.write(
            {"active": True}
        )
        return res


class BudgetPlanLine(models.Model):
    _inherit = "budget.plan.line"

    revision_number = fields.Integer(related="plan_id.revision_number")

    def _domain_budget_control(self):
        domain = super()._domain_budget_control()
        # Since we use revision, ensure having both active/inactive
        domain.remove(("active", "=", True))
        domain.extend([("revision_number", "=", self.revision_number)])
        return domain
