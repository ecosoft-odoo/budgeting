# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class BudgetPlan(models.Model):
    _name = "budget.plan"
    _inherit = ["mail.thread"]
    _description = "Budget Plan"
    _order = "id desc"

    name = fields.Char(
        required=True,
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    budget_period_id = fields.Many2one(
        comodel_name="budget.period",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    budget_control_ids = fields.One2many(
        comodel_name="budget.control",
        inverse_name="plan_id",
        context={"active_test": False},
    )
    budget_control_count = fields.Integer(
        string="# of Budget Control",
        compute="_compute_budget_control_related_count",
        store=True,
        help="Count budget control in Plan",
    )
    total_amount = fields.Monetary(compute="_compute_total_amount")
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.user.company_id,
        required=False,
        string="Company",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency", related="company_id.currency_id"
    )
    plan_line = fields.One2many(
        comodel_name="budget.plan.line",
        inverse_name="plan_id",
        copy=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        context={"active_test": False},
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

    @api.depends("plan_line")
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.plan_line.mapped("amount"))

    @api.depends("budget_control_ids")
    def _compute_budget_control_related_count(self):
        for rec in self:
            rec.budget_control_count = len(rec.budget_control_ids)

    def button_open_budget_control(self):
        self.ensure_one()
        action = {
            "name": _("Budget Control Sheet"),
            "type": "ir.actions.act_window",
            "res_model": "budget.control",
            "context": {"create": False, "active_test": False},
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
        Analytic = self.env["account.analytic.account"]
        plan_analytic = self.plan_line.mapped("analytic_account_id")
        analytic_ids = Analytic.search(
            [
                ("budget_period_id", "=", self.budget_period_id.id),
                ("id", "not in", plan_analytic.ids),
            ]
        )
        if analytic_ids:
            lines = list(
                map(
                    lambda l: (0, 0, {"analytic_account_id": l.id}),
                    analytic_ids,
                )
            )
            self.write({"plan_line": lines})
        return True

    def _get_analytic_plan(self):
        return self.plan_line.filtered("active").mapped("analytic_account_id")

    def _get_context_wizard(self):
        ctx = {
            "active_model": "budget.plan",
            "active_ids": self.ids,
        }
        return ctx

    def action_create_budget_control(self):
        self.ensure_one()
        GenerateBudgetControl = self.env["generate.budget.control"]
        analytic_plan = self._get_analytic_plan()
        ctx = self._get_context_wizard()
        budget_period = self.budget_period_id
        generate_budget_id = GenerateBudgetControl.with_context(ctx).create(
            {
                "budget_period_id": budget_period.id,
                "budget_id": budget_period.mis_budget_id.id,
                "budget_plan_id": self.id,
                "analytic_account_ids": [(6, 0, analytic_plan.ids)],
            }
        )
        budget_control_view = (
            generate_budget_id.action_generate_budget_control()
        )
        return budget_control_view

    def action_done(self):
        lines = self.mapped("plan_line")
        for line in lines:
            line.allocated_amount = line.released_amount = line.amount
        self.write({"state": "done"})

    def action_cancel(self):
        self.write({"state": "cancel"})

    def action_draft(self):
        self.write({"state": "draft"})


class BudgetPlanLine(models.Model):
    _name = "budget.plan.line"
    _description = "Budget Plan Line"

    plan_id = fields.Many2one(
        comodel_name="budget.plan",
    )
    budget_period_id = fields.Many2one(
        comodel_name="budget.period", related="plan_id.budget_period_id"
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        required=True,
    )
    allocated_amount = fields.Float(readonly=True)
    released_amount = fields.Float(
        compute="_compute_released_amount", store=True, readonly=True
    )
    amount = fields.Float()
    spent = fields.Float(readonly=True)
    active = fields.Boolean(default=True)

    @api.depends("plan_id.budget_control_ids.released_amount")
    def _compute_released_amount(self):
        for rec in self:
            budget_control_ids = rec.plan_id.budget_control_ids
            if budget_control_ids:
                budget_control = budget_control_ids.filtered(
                    lambda l: l.released_amount != rec.released_amount
                    and l.analytic_account_id == rec.analytic_account_id
                )
                if budget_control:
                    rec.released_amount = budget_control.released_amount
