# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class GenerateBudgetControl(models.TransientModel):
    _inherit = "generate.budget.control"

    budget_plan_id = fields.Many2one(
        comodel_name="budget.plan",
    )

    def _get_existing_budget(self):
        """ Update allocated amount from budget plan """
        existing_budget_controls = super()._get_existing_budget()
        if self.budget_plan_id:
            plan_line = self.budget_plan_id.plan_line
            existing_budget_controls._update_allocated_amount(plan_line)
        return existing_budget_controls

    def _prepare_value_duplicate(self, vals):
        if self.budget_plan_id:
            plan_date_range_id = (
                self.budget_period_id.plan_date_range_type_id.id
            )
            budget_id = self.budget_id.id
            budget_name = self.budget_period_id.name
            return list(
                map(
                    lambda l: {
                        "name": "{} :: {}".format(
                            budget_name, l["analytic_account_id"].name
                        ),
                        "budget_id": budget_id,
                        "analytic_account_id": l["analytic_account_id"].id,
                        "plan_date_range_type_id": plan_date_range_id,
                        "allocated_amount": l["allocated_amount"],
                    },
                    vals,
                )
            )
        return super()._prepare_value_duplicate(vals)

    def _prepare_value_plan(self, plan_line):
        vals = [
            {
                "analytic_account_id": x.analytic_account_id,
                "allocated_amount": x.allocated_amount,
            }
            for x in plan_line
        ]
        return vals

    def _prepare_value(self, analytic):
        """ Prepare allocated amount to Budget Control """
        if self.budget_plan_id:
            plan_line = self.budget_plan_id.plan_line.filtered(
                lambda l: l.analytic_account_id in analytic
            )
            return self._prepare_value_plan(plan_line)
        else:
            return super()._prepare_value(analytic)
