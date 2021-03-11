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
    revision_number = fields.Integer(readonly=True)

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

    def _update_allocated_amount(self, budget_control_ids):
        for new_bc in budget_control_ids:
            plan_line = self.plan_line.filtered(
                lambda l: l.analytic_account_id == new_bc.analytic_account_id
            )
            new_bc.write({"allocated_amount": plan_line.allocated_amount})

    def _get_context_wizard(self):
        ctx = super()._get_context_wizard()
        ctx.update({"revision": self.revision_number})
        return ctx

    def _filter_budget_control_active(self, old_plan):
        """
        - Filter out analytic is inactive
        - Check case back to active but analytic was created and inactive.
        - Create new budget with new analytic (if any)
            i.e. Case back to active on Budget Plan Line
            ===================================================================
            Analytic    Revision    Active      |   Budget Control  Revision
            ===================================================================
            A1          1           True        |   A1              1
            A2          1           True        |   A2              1
            -------------------- New Revision --------------------
            A1          2           True        |   A1              2
            A2          2           False       |
            A3          2           True        |   A3              2 (new)
            -------------------- New Revision --------------------
            A1          3           True        |   A1              3
            A2          3           True        |   A2              3
            A3          3           True        |   A3              3
        """
        BudgetControl = self.env["budget.control"]
        plan_analytic = self.plan_line.filtered("active").mapped(
            "analytic_account_id"
        )
        budget_control_inactive = old_plan.budget_control_ids.filtered(
            lambda l: l.analytic_account_id.id not in plan_analytic.ids
        )
        budget_control_active = (
            old_plan.budget_control_ids - budget_control_inactive
        )
        budget_control_inactive.write({"active": False})
        # check analytic old revision and current
        old_plan_analytic = old_plan.plan_line.filtered("active").mapped(
            "analytic_account_id"
        )
        new_plan_analytic = plan_analytic.filtered(
            lambda l: l.id not in old_plan_analytic.ids
        )
        bc_old = BudgetControl.search(
            [
                ("analytic_account_id", "in", new_plan_analytic.ids),
                ("active", "=", False),
            ],
            order="id desc",
            limit=1,
        )
        if bc_old:
            action_old_bc = bc_old.create_revision()
            domain = ast.literal_eval(action_old_bc.get("domain", False))
            budget_control_ids = BudgetControl.browse(domain[0][2])
            budget_control_ids.write(
                {
                    "revision_number": self.revision_number,
                    "active": True,
                    "plan_id": self.id,
                }
            )
            for bc in budget_control_ids:
                bc.write(
                    {
                        "name": "%s-%02d"
                        % (bc.unrevisioned_name, self.revision_number)
                    }
                )
            self._update_allocated_amount(budget_control_ids)
        # Create new budget control, if new analytic
        self.action_create_budget_control()
        return budget_control_active

    def create_revision_budget_control(self):
        """ Crete new revision Budget Control and update to new plan """
        BudgetControl = self.env["budget.control"]
        for rec in self:
            old_lasted = rec.old_revision_ids[0]
            old_lasted._check_state_budget_control()
            budget_control_active = rec._filter_budget_control_active(
                old_lasted
            )
            action_bc = budget_control_active.create_revision()
            domain = ast.literal_eval(action_bc.get("domain", False))
            budget_control_ids = BudgetControl.browse(domain[0][2])
            rec._update_allocated_amount(budget_control_ids)
            budget_control_ids.write({"plan_id": rec.id})
            BudgetControl += budget_control_ids
        return BudgetControl

    def create_revision(self):
        """ Update amount from old budget control to new plan line """
        self._check_state_budget_control()
        res = super().create_revision()
        domain = ast.literal_eval(res.get("domain", False))
        new_plan = self.browse(domain[0][2])
        new_plan_line = new_plan.mapped("plan_line")
        for line in new_plan_line:
            budget_control = line.analytic_account_id.budget_control_id
            current_budget = budget_control.current_revision_id
            line.write(
                {
                    "allocated_amount": current_budget.allocated_amount,
                    "released_amount": current_budget.released_amount,
                    "amount": current_budget.released_amount,
                }
            )
        return res


class BudgetPlanLine(models.Model):
    _inherit = "budget.plan.line"

    revision_number = fields.Integer(related="plan_id.revision_number")
