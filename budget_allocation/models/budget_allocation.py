# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class BudgetAllocation(models.Model):
    _name = "budget.allocation"
    _inherit = ["mail.thread"]
    _description = "Budget Allocation"

    name = fields.Char(
        required=True,
        readonly=True,
        states={"draft": [("readonly", "=", False)]},
    )
    budget_period_id = fields.Many2one(
        comodel_name="budget.period",
        required=True,
        default=lambda self: self.env[
            "budget.period"
        ]._get_eligible_budget_period(),
        readonly=True,
        states={"draft": [("readonly", "=", False)]},
    )
    allocation_line_ids = fields.One2many(
        comodel_name="budget.allocation.line",
        inverse_name="budget_allocation_id",
        readonly=True,
        states={"draft": [("readonly", "=", False)]},
    )
    plan_id = fields.Many2one(comodel_name="budget.plan", copy=False)
    total_amount = fields.Monetary(
        compute="_compute_total_amount", help="Sum of amount allocation"
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.user.company_id,
        required=True,
        string="Company",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency", related="company_id.currency_id"
    )
    active = fields.Boolean(default=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
        copy=False,
    )

    @api.depends("allocation_line_ids")
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(
                rec.allocation_line_ids.mapped("budget_amount")
            )

    def action_done(self):
        for rec in self:
            if rec.plan_id:
                rec.plan_id.write({"init_amount": rec.total_amount})
        return self.write({"state": "done"})

    def action_draft(self):
        return self.write({"state": "draft"})

    def action_cancel(self):
        return self.write({"state": "cancel"})

    def _prepare_vals_budget_plan(self):
        vals = {
            "name": self.name,
            "budget_period_id": self.budget_period_id.id,
            "budget_allocation_id": self.id,
            "init_amount": self.total_amount,
        }
        return vals

    def action_generate_budget_plan(self):
        self.ensure_one()
        BudgetPlan = self.env["budget.plan"]
        vals = self._prepare_vals_budget_plan()
        plan_id = BudgetPlan.create(vals)
        self.write({"plan_id": plan_id.id})
        plan_id.action_generate_plan()
        return plan_id

    def button_open_budget_plan(self):
        self.ensure_one()
        return {
            "name": _("Budget Plan"),
            "type": "ir.actions.act_window",
            "res_model": "budget.plan",
            "view_mode": "form",
            "res_id": self.plan_id.id,
            "context": self.env.context,
        }


class BudgetAllocationLine(models.Model):
    _name = "budget.allocation.line"
    _description = "Budget Allocation Line"
    _check_company_auto = True

    budget_allocation_id = fields.Many2one(
        comodel_name="budget.allocation",
        string="Budget Allocation",
        ondelete="cascade",
        required=True,
        readonly=True,
        check_company=True,
    )
    budget_period_id = fields.Many2one(
        comodel_name="budget.period",
        related="budget_allocation_id.budget_period_id",
        store=True,
    )
    date_from = fields.Date(
        related="budget_period_id.bm_date_from",
        store=True,
    )
    date_to = fields.Date(
        related="budget_period_id.bm_date_to",
        store=True,
    )
    budget_control_id = fields.Many2one(
        comodel_name="budget.control",
        readonly=True,
    )
    name = fields.Char(string="Description")
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        required=True,
        index=True,
    )
    budget_amount = fields.Monetary(string="Amount")
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.user.company_id,
        required=False,
        string="Company",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency", related="company_id.currency_id"
    )
