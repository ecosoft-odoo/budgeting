# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ast

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BudgetPlan(models.Model):
    _name = "budget.plan"
    _inherit = ["budget.plan", "base.revision"]

    current_revision_id = fields.Many2one(
        comodel_name="budget.plan",
        index=True,
    )
    old_revision_ids = fields.One2many(
        comodel_name="budget.plan",
    )
    init_revision = fields.Boolean(
        string="Initial Version", default=True, readonly=True
    )
    revision_number = fields.Integer()
    enable_revision_number = fields.Boolean(compute="_compute_group_revision_number")

    @api.depends("revision_number")
    def _compute_group_revision_number(self):
        group_enable_revision = self.env.user.has_group(
            "budget_control_revision.group_enable_revision"
        )
        self.update({"enable_revision_number": group_enable_revision})
        return True

    def action_update_plan(self):
        """
        Update consumed amount plan,
        For case new revision budget plan but not created budget control.
        """
        super().action_update_plan()
        for rec in self:
            if not (rec.init_revision or rec.budget_control_ids):
                # Search all budget controls that matched with analytics and budget period
                BudgetControl = self.env["budget.control"]
                analytics = rec.plan_line.mapped("analytic_account_id")
                budget_controls = BudgetControl.search(
                    [
                        ("analytic_account_id", "in", analytics.ids),
                        ("date_from", "<=", rec.budget_period_id.bm_date_from),
                        ("date_to", ">=", rec.budget_period_id.bm_date_to),
                    ]
                )
                # Group budget control (key: analytic_account_id)
                group_budget_controls = {}
                for budget_control in budget_controls:
                    analytic_account_id = budget_control.analytic_account_id.id
                    if analytic_account_id not in group_budget_controls:
                        group_budget_controls[analytic_account_id] = budget_control
                    else:
                        group_budget_controls[analytic_account_id] += budget_control
                # Update consumed and released amount from previous budget control
                for line in rec.plan_line:
                    prev_control = group_budget_controls.get(
                        line.analytic_account_id.id, BudgetControl
                    ).sorted("revision_number")[-1:]
                    if prev_control:
                        line.write(
                            {
                                "amount_consumed": prev_control.amount_consumed,
                                "released_amount": prev_control.released_amount,
                            }
                        )

    def button_open_budget_control(self):
        # Beacuse we want to use revision number, and inactive should be shown
        action = super().button_open_budget_control()
        if not self.budget_control_ids.filtered("active"):
            action["context"]["search_default_inactive"] = True
        return action

    def action_create_update_budget_control(self):
        self = self.with_context(active_test=False)
        no_bc_lines = self.plan_line.filtered_domain(
            [("budget_control_ids", "=", False)]
        )
        plan_line_revision = self.env["budget.plan.line"]
        analytics = no_bc_lines.mapped("analytic_account_id")
        # Search all budget controls that matched with analytics and budget period
        BudgetControl = self.env["budget.control"]
        budget_controls = BudgetControl.search(
            [
                ("analytic_account_id", "in", analytics.ids),
                ("date_from", "<=", self.budget_period_id.bm_date_from),
                ("date_to", ">=", self.budget_period_id.bm_date_to),
            ]
        )
        # Group budget control (by analytic account)
        group_budget_controls = {}
        for budget_control in budget_controls:
            analytic_account_id = budget_control.analytic_account_id.id
            if analytic_account_id not in group_budget_controls:
                group_budget_controls[analytic_account_id] = budget_control
            else:
                group_budget_controls[analytic_account_id] += budget_control
        # Create budget control revision
        for analytic in analytics:
            prev_control = group_budget_controls.get(analytic.id, BudgetControl).sorted(
                "revision_number"
            )[-1:]
            if prev_control:
                # Check state budget control for user manual cancel.
                if prev_control.state != "cancel" and prev_control.active:
                    raise UserError(
                        _(
                            "In order to create new budget control version, "
                            "all current ones must be cancelled."
                        )
                    )
                prev_control.with_context(
                    revision_number=self.revision_number
                ).create_revision()
                plan_line_revision += self.plan_line.filtered_domain(
                    [("analytic_account_id", "=", analytic.id)]
                )
        return super(
            BudgetPlan,
            self.with_context(
                plan_line_revision=plan_line_revision,
                revision_number=self.revision_number,
                init_revision=self.init_revision,
            ),
        ).action_create_update_budget_control()

    def create_revision(self):
        """Create budget plan revision and all its budget controls"""
        self = self.sudo().with_context(active_test=False)
        res = super().create_revision()
        # Based on new budget_plan, create new budget controls by create_revision()
        new_plan = self.search(ast.literal_eval(res.get("domain", False)))
        new_plan.ensure_one()
        new_plan.write({"active": True, "init_revision": False})
        # By default, there should be no budget_controls, but in case there is,
        # so we want to make sure not to create it.
        new_plan.plan_line.invalidate_cache()
        # Ensure all budget controls are set as active to start
        new_plan.invalidate_cache()
        new_plan.with_context(active_test=False).budget_control_ids.write(
            {"active": True, "init_revision": False}
        )
        return res


class BudgetPlanLine(models.Model):
    _inherit = "budget.plan.line"

    revision_number = fields.Integer(related="plan_id.revision_number")

    def _domain_budget_control(self):
        domain = super()._domain_budget_control()
        domain.extend([("revision_number", "=", self.revision_number)])
        return domain
