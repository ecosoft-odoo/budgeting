# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ast

from odoo import _, fields, models
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

    def create_revision_budget_control(self):
        """ Crete new revision Budget Control and update to new plan """
        self.ensure_one()
        BudgetControl = self.env["budget.control"]
        budget_controls = self.old_revision_ids[0].budget_control_ids
        control_state = set(budget_controls.mapped("state"))
        if len(control_state) != 1 or "cancel" not in control_state:
            raise UserError(
                _(
                    "Can not revision. All budget control have to state 'cancel'"
                )
            )
        action = budget_controls.with_context(
            {"active_model": "budget.control"}
        ).create_revision()
        domain = ast.literal_eval(action.get("domain", False))
        budget_control_ids = BudgetControl.browse(domain[0][2])
        budget_control_ids.write({"plan_id": self.id})
        return action

    def create_revision(self):
        """
        Step to create new revision:
        - Create new revision Budget Plan without Source of Fund Plan.
        - Create new revision Source of Fund Plan and
          update new Budget Plan on all source of fund plan.
        - Remove plan from source of fund plan for generate new plan.
        """
        res = super().create_revision()
        SourceFundPlan = self.env["budget.source.fund.plan"]
        domain_budget_plan = ast.literal_eval(res.get("domain", False))
        new_budget_plan_ids = self.browse(domain_budget_plan[0][2])
        # loop case multi
        for rec in new_budget_plan_ids:
            old_lasted = rec.old_revision_ids[0]
            action_fund_plan = old_lasted.fund_plan_line.create_revision()
            domain_fund_plan = ast.literal_eval(
                action_fund_plan.get("domain", False)
            )
            new_plan_ids = SourceFundPlan.browse(domain_fund_plan[0][2])
            new_plan_ids.write({"plan_id": False, "state": "draft"})
        return res
