# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ast

from odoo import fields, models


class BudgetAllocation(models.Model):
    _name = "budget.allocation"
    _inherit = ["budget.allocation", "base.revision"]

    current_revision_id = fields.Many2one(
        comodel_name="budget.allocation",
    )
    old_revision_ids = fields.One2many(
        comodel_name="budget.allocation",
    )
    init_revision = fields.Boolean(default=True, readonly=True)

    _sql_constraints = [
        (
            "budget_period_uniq",
            "unique(unrevisioned_name, revision_number, budget_period_id)",
            "Budget period and revision must be unique.",
        )
    ]

    def _get_new_rev_data(self, new_rev_number):
        """Update revision budget allocation is not initial revision"""
        self.ensure_one()
        new_rev_dict = super()._get_new_rev_data(new_rev_number)
        new_rev_dict["init_revision"] = False
        return new_rev_dict

    def action_done(self):
        """Create new revision budget plan, when new revision allocation and not plan yet"""
        self = self.with_context(active_test=False)
        self_revision = self.filtered(lambda l: l.old_revision_ids and not l.plan_id)
        BudgetPlan = self.env["budget.plan"]
        for rec in self_revision:
            budget_plan = BudgetPlan.search(
                [
                    ("budget_period_id", "=", rec.budget_period_id.id),
                ],
                order="revision_number desc",
                limit=1,
            )
            new_plan_val = budget_plan.with_context(
                revision_number=rec.revision_number
            ).create_revision()
            domain_list = ast.literal_eval(new_plan_val["domain"])
            rec.write({"plan_id": domain_list[0][2][0]})
        return super().action_done()
