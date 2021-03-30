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
        self.write({"enable_revision_number": group_enable_revision})
        return True

    @api.depends("budget_control_ids", "revision_number")
    def _compute_budget_control_related_count(self):
        return super()._compute_budget_control_related_count()

    def _check_state_budget_control(self):
        for rec in self:
            bc_state = set(rec.budget_control_ids.mapped("state"))
            if len(bc_state) != 1 or "cancel" not in bc_state:
                raise UserError(
                    _(
                        "Can not revision. All budget control have to state 'cancel'"
                    )
                )

    def _get_context_wizard(self):
        ctx = super()._get_context_wizard()
        ctx.update({"revision": self.revision_number})
        return ctx

    def _hook_new_budget_plan(self, new_plan):
        """ Hooks for do something new plan """
        return True

    def create_revision_budget_control(self):
        """
        Crete new revision Budget Control following:
            1. Inactive current version budget control
            2. Create new budget control from budget plan
        """
        ctx = self._context.copy()
        ctx.update({"revision_number": self.revision_number})
        for rec in self:
            old_lasted = rec.old_revision_ids[0]
            old_lasted._check_state_budget_control()
            old_lasted.budget_control_ids.write({"active": False})
            rec.action_create_budget_control()
        return True

    def action_create_budget_control(self):
        res = super().action_create_budget_control()
        self.ensure_one()
        self.init_revision = False
        return res

    def create_revision(self):
        """ Update amount from old budget control to new plan line """
        # TODO: this function should be multi???
        self._check_state_budget_control()
        res = super().create_revision()
        domain = ast.literal_eval(res.get("domain", False))
        new_plan = self.browse(domain[0][2])
        self._hook_new_budget_plan(new_plan)
        new_plan_line = new_plan.mapped("plan_line")
        for line in new_plan_line:
            budget_controls = line.analytic_account_id.budget_control_ids
            # Use budget_control for this period.
            budget_control = budget_controls.filtered_domain(
                [
                    ("budget_period_id", "=", self.budget_period_id.id),
                    ("active", "=", True),
                ]
            )
            allocated_amount = budget_control.allocated_amount
            released_amount = budget_control.released_amount
            if budget_control.current_revision_id:
                allocated_amount = (
                    budget_control.current_revision_id.allocated_amount
                )
                released_amount = (
                    budget_control.current_revision_id.released_amount
                )
            line.write(
                {
                    "allocated_amount": allocated_amount,
                    "released_amount": released_amount,
                    "amount": released_amount,
                }
            )
        new_plan.action_update_amount_consumed()
        return res


class BudgetPlanLine(models.Model):
    _inherit = "budget.plan.line"

    revision_number = fields.Integer(related="plan_id.revision_number")
