# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import ast

from odoo import _, models
from odoo.exceptions import UserError


class BudgetControl(models.Model):
    _inherit = "budget.control"

    def _domain_kpi_expression(self):
        """ Update kpi_ids, case budget plan revision """
        kpi_ids = self._context.get("kpi_ids", False)
        ctx = self._context.copy()
        create_revision = self._context.get("create_revision", False)
        if kpi_ids and create_revision:
            kpi_id = False
            analytic_id = self.analytic_account_id.id
            kpi = list(
                filter(
                    lambda kpi: kpi.get(analytic_id, False),
                    kpi_ids,
                )
            )
            if kpi:
                kpi_id = kpi[0].get(analytic_id)
            ctx["kpi_ids"] = kpi_id
        domain_kpi = super(
            BudgetControl, self.with_context(ctx)
        )._domain_kpi_expression()
        return domain_kpi

    def _keep_origin_plan(self, budget_control):
        """
        Keep plan version 0 and update plan revision
        Step to update revision:
        1. Check budget control must be state done all on plan.
        2. Create revision plan to v1 - Keep origin plan v0
        3. Create revision budget control from plan v1 -
            Keep origin budget control v0
        4. Update state budget control v1 to control.
        """
        BudgetPlan = self.env["budget.plan"]
        plan = budget_control.mapped("plan_id")
        # TODO: Not test case: Create budget control direct.
        if len(set(plan)) > 1:
            raise UserError(_("You can not control budget more than 1 plan."))
        plan_all_state = plan.budget_control_ids.mapped("state")
        if len(set(plan_all_state)) == 1 and "done" in plan_all_state:
            budget_control.action_cancel()
            # Revision Plan
            action_plan = plan.create_revision()
            domain = ast.literal_eval(action_plan.get("domain", False))
            new_plan_revision = BudgetPlan.browse(domain[0][2])
            new_plan_revision.action_done()
            new_budget_control = new_plan_revision.with_context(
                {"keep_origin": True}
            ).create_revision_budget_control()
            new_budget_control.action_done()
            return new_budget_control
        # Case control budget control from plan not completed
        budget_control.action_cancel()
        action_control = budget_control.create_revision()
        domain = ast.literal_eval(action_control.get("domain", False))
        new_budget_control_revision = self.browse(domain[0][2])
        new_budget_control_revision.action_done()
        return new_budget_control_revision

    def action_done(self):
        res = super().action_done()
        origin_budget = self.filtered(lambda l: l.revision_number == 0)
        keep_origin_plan = self.env.user.has_group(
            "budget_plan_revision.keep_origin_plan"
        )
        if keep_origin_plan and origin_budget:
            new_budget_control = self._keep_origin_plan(origin_budget)
            if new_budget_control:
                return {
                    "name": _("Budget Control Sheet"),
                    "type": "ir.actions.act_window",
                    "res_model": "budget.control",
                    "view_mode": "list,form",
                    "domain": [("id", "in", new_budget_control.ids)],
                }
        return res
