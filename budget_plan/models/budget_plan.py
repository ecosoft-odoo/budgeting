# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class BudgetPlan(models.Model):
    _name = "budget.plan"
    _inherit = ["mail.thread"]
    _description = "Budget Plan"

    name = fields.Char(required=True, tracking=True)
    budget_period_id = fields.Many2one(
        comodel_name="budget.period",
        required=True,
    )
    fund_plan_line = fields.One2many(
        comodel_name="budget.source.fund.plan",
        inverse_name="plan_id",
    )
    budget_control_ids = fields.One2many(
        comodel_name="budget.control",
        inverse_name="plan_id",
    )
    budget_control_count = fields.Integer(
        string="# of Budget Control",
        compute="_compute_budget_control_related_count",
        help="Count budget control in Plan",
    )
    active = fields.Boolean(default=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
        tracking=True,
    )

    def _compute_budget_control_related_count(self):
        self.budget_control_count = len(self.budget_control_ids)

    def button_open_budget_control(self):
        self.ensure_one()
        action = {
            "name": _("Budget Control Sheet"),
            "type": "ir.actions.act_window",
            "res_model": "budget.control",
            "context": {"create": False},
        }
        if len(self.budget_control_ids) == 1:
            action.update(
                {
                    "view_mode": "form",
                    "res_id": self.budget_control_ids.id,
                }
            )
        else:
            action.update(
                {
                    "view_mode": "list,form",
                    "domain": [("id", "in", self.budget_control_ids.ids)],
                }
            )
        return action

    def action_generate_plan(self):
        self.ensure_one()
        SourceFundPlan = self.env["budget.source.fund.plan"]
        fund_plan = SourceFundPlan.search(
            [
                ("budget_period_id", "=", self.budget_period_id.id),
                ("state", "=", "done"),
            ]
        )
        fund_plan.write({"plan_id": self.id})
        return fund_plan

    def action_plan_generate_budget_control(self):
        analytic_plan = self.mapped("fund_plan_line.allocation_line").mapped(
            "analytic_account_id"
        )
        return {
            "name": _("Generate Budget Control Sheet"),
            "res_model": "generate.budget.control",
            "view_mode": "form",
            "context": {
                "active_model": "budget.plan",
                "active_ids": self.ids,
                "default_analytic_account_ids": analytic_plan.ids,
            },
            "target": "new",
            "type": "ir.actions.act_window",
        }

    def action_done(self):
        self.write({"state": "done"})
        return True

    def action_cancel(self):
        self.budget_control_ids.action_cancel()
        self.write({"state": "cancel"})
        return True

    def action_draft(self):
        self.write({"state": "draft"})
        return True
