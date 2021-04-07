# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


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
    date_from = fields.Date(related="budget_period_id.bm_date_from")
    date_to = fields.Date(related="budget_period_id.bm_date_to")
    budget_control_ids = fields.One2many(
        comodel_name="budget.control",
        compute="_compute_budget_control_ids",
        context={"active_test": False},
    )
    budget_control_count = fields.Integer(
        string="# of Budget Control",
        compute="_compute_budget_control_related_count",
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
            ("confirm", "Confirmed"),
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

    def _domain_budget_control(self, analytics):
        self.ensure_one()
        return [
            ("budget_period_id", "=", self.budget_period_id.id),
            ("analytic_account_id", "in", analytics.ids),
        ]

    def _compute_budget_control_ids(self):
        """ Find all budget controls of the same period """
        for rec in self:
            analytics = rec.plan_line.mapped("analytic_account_id")
            domain = rec._domain_budget_control(analytics)
            rec.budget_control_ids = (
                self.env["budget.control"]
                .with_context(active_test=False)
                .search(domain)
            )

    def _compute_budget_control_related_count(self):
        for rec in self:
            rec.budget_control_count = len(rec.budget_control_ids)

    def action_update_amount_consumed(self):
        for rec in self:
            for line in rec.plan_line:
                budget_control = line.analytic_account_id.budget_control_ids
                line.amount_consumed = sum(
                    budget_control.mapped("amount_consumed")
                )

    def button_open_budget_control(self):
        self.ensure_one()
        ctx = self._context.copy()
        ctx.update({"create": False, "active_test": True})
        if not self.budget_control_ids.filtered("active"):
            ctx.update({"search_default_inactive": True})
        action = {
            "name": _("Budget Control Sheet"),
            "type": "ir.actions.act_window",
            "res_model": "budget.control",
            "context": ctx,
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
        return self.plan_line.mapped("analytic_account_id")

    def _get_context_wizard(self):
        ctx = {
            "active_model": "budget.plan",
            "active_ids": self.ids,
        }
        return ctx

    def _update_active_budget_control(
        self, analytic_plan, budget_control=False
    ):
        """ Inactive budget control is not in budget plan """
        self.ensure_one()
        if not budget_control:
            budget_control = self.budget_control_ids
        budget_control_inactive = budget_control.filtered(
            lambda l: l.analytic_account_id.id not in analytic_plan.ids
        )
        budget_control_inactive.write({"state": "cancel", "active": False})

    def _generate_budget_control(self, analytic_plan):
        GenerateBudgetControl = self.env["generate.budget.control"]
        ctx = self._get_context_wizard()
        budget_period = self.budget_period_id
        generate_budget_id = GenerateBudgetControl.with_context(ctx).create(
            {
                "budget_period_id": budget_period.id,
                "mis_report_id": budget_period.report_id.id,
                "budget_id": budget_period.mis_budget_id.id,
                "budget_plan_id": self.id,
                "analytic_account_ids": [(6, 0, analytic_plan.ids)],
            }
        )
        budget_control_view = (
            generate_budget_id.action_generate_budget_control()
        )
        return budget_control_view

    def action_create_update_budget_control(self):
        self.ensure_one()
        analytic_plan = self._get_analytic_plan()
        budget_control_view = self._generate_budget_control(analytic_plan)
        self._update_active_budget_control(analytic_plan)
        return budget_control_view

    def action_confirm(self):
        self.action_update_amount_consumed()
        prec_digits = self.env.user.company_id.currency_id.decimal_places
        lines = self.mapped("plan_line")
        for line in lines:
            if (
                float_compare(
                    line.amount,
                    line.amount_consumed,
                    precision_digits=prec_digits,
                )
                == -1
            ):
                raise UserError(
                    _(
                        "{} has amount less than consumed.".format(
                            line.analytic_account_id.display_name
                        )
                    )
                )
            line.allocated_amount = line.released_amount = line.amount
        self.write({"state": "confirm"})

    def action_done(self):
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
    amount_consumed = fields.Float(string="Consumed", readonly=True)
    active = fields.Boolean(default=True)

    @api.depends("plan_id.budget_control_ids.released_amount")
    def _compute_released_amount(self):
        for rec in self:
            budget_controls = rec.plan_id.budget_control_ids
            release = {
                x.analytic_account_id.id: x.released_amount
                for x in budget_controls
            }
            rec.released_amount = release.get(rec.analytic_account_id.id)
