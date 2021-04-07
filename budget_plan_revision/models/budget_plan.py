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

    def _domain_budget_control(self, analytics):
        domain = super()._domain_budget_control(analytics)
        return domain + [("revision_number", "=", self.revision_number)]

    @api.depends("revision_number")
    def _compute_group_revision_number(self):
        group_enable_revision = self.env.user.has_group(
            "budget_plan_revision.group_enable_revision"
        )
        self.update({"enable_revision_number": group_enable_revision})
        return True

    def _cancel_budget_control(self):
        self.ensure_one()
        budget_control = self.budget_control_ids
        budget_control.action_cancel()
        return budget_control

    def _get_context_wizard(self):
        ctx = super()._get_context_wizard()
        ctx.update({"revision": self.revision_number})
        return ctx

    def _hook_new_budget_plan(self, new_plan):
        """ Hooks for do something new plan """
        new_plan.init_revision = False
        return True

    def _update_new_analytic_plan(self, analytic_plan, budget_control):
        """
        Add new analytic in budget plan,
        it should be new revision from old lasted and overwrite number.
        """
        Analytic = self.env["account.analytic.account"]
        ctx = self._context.copy()
        ctx.update(
            {"revision_number": self.revision_number, "skip_revision": True}
        )
        if len(analytic_plan) > len(budget_control):
            new_analytic = analytic_plan - budget_control.mapped(
                "analytic_account_id"
            )
            for analytic in new_analytic:
                bc_current = analytic.budget_control_ids.filtered(
                    lambda l: l.budget_period_id == self.budget_period_id
                )
                if not bc_current:
                    Analytic += analytic
                bc_current.with_context(ctx).create_revision()
            # new analytic, never revision
            if Analytic:
                self._generate_budget_control(Analytic)
                Analytic.mapped("budget_control_ids")

    def action_revision_budget_control(self):
        """
        Crete new revision Budget Control following:
            1. Inactive current version budget control
            2. Create new budget control from budget plan
        """
        self.ensure_one()
        BudgetControl = self.env["budget.control"]
        ctx = self._context.copy()
        ctx.update({"revision_number": self.revision_number})
        analytic_plan = self._get_analytic_plan()
        # Old version budget control
        old_lasted = self.old_revision_ids[0]
        self._update_active_budget_control(
            analytic_plan, old_lasted.budget_control_ids
        )
        self._update_new_analytic_plan(
            analytic_plan, old_lasted.budget_control_ids
        )
        old_budget_control = old_lasted._cancel_budget_control()
        # New version budget control
        action_bc = old_budget_control.create_revision()
        domain = ast.literal_eval(action_bc.get("domain", False))
        budget_controls = BudgetControl.browse(domain[0][2])
        budget_controls._update_allocated_amount(self.plan_line)
        return True

    def action_create_update_budget_control(self):
        self.ensure_one()
        if not (self.init_revision or self.budget_control_ids):
            return self.action_revision_budget_control()
        return super().action_create_update_budget_control()

    def create_revision(self):
        """ Update amount from old budget control to new plan line """
        res = super().create_revision()
        domain = ast.literal_eval(res.get("domain", False))
        new_plan = self.browse(domain[0][2])
        self._hook_new_budget_plan(new_plan)
        new_plan_line = new_plan.mapped("plan_line")
        for line in new_plan_line:
            # Use budget_control for this period.
            budget_control = (
                line.analytic_account_id.budget_control_ids.filtered(
                    lambda l: l.budget_period_id.id == self.budget_period_id.id
                )
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
