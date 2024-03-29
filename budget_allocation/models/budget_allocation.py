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
        default=lambda self: self.env["budget.period"]._get_eligible_budget_period(),
        readonly=True,
        index=True,
        states={"draft": [("readonly", "=", False)]},
    )
    allocation_line_ids = fields.One2many(
        comodel_name="budget.allocation.line",
        inverse_name="budget_allocation_id",
        readonly=True,
        context={"active_test": False},
        states={"draft": [("readonly", "=", False)]},
    )
    plan_id = fields.Many2one(
        comodel_name="budget.plan",
        index=True,
        copy=False,
    )
    total_amount = fields.Monetary(
        compute="_compute_total_amount", help="Sum of amount allocation"
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.user.company_id,
        required=True,
        index=True,
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
            rec.total_amount = sum(rec.allocation_line_ids.mapped("allocated_amount"))

    def action_done(self):
        for rec in self:
            # Write initail on budget plan
            if rec.plan_id:
                rec.plan_id.write({"init_amount": rec.total_amount})
            # Update released amount following allocated amount
            allocation_lines = rec.allocation_line_ids.filtered(
                lambda x: x.allocated_amount != x.released_amount
            )
            for line in allocation_lines:
                line.write({"released_amount": line.allocated_amount})
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
        # Create budget plan from allocation
        vals = self._prepare_vals_budget_plan()
        budget_plan = self.env["budget.plan"].create(vals)
        # Link allocation and budget plan
        self.write({"plan_id": budget_plan.id})
        # Update budget plan lines
        budget_plan.action_update_plan()
        return budget_plan

    def _get_domain_open_analytic(self):
        self.ensure_one()
        return [
            ("bm_date_to", ">=", self.budget_period_id.bm_date_from),
            ("bm_date_from", "<=", self.budget_period_id.bm_date_to),
        ]

    def _get_domain_open_allocation(self):
        self.ensure_one()
        return [("budget_allocation_id", "=", self.id)]

    def button_open_analytic(self):
        self.ensure_one()
        domain = self._get_domain_open_analytic()
        list_view = self.env.ref("budget_control.view_budget_analytic_list").id
        form_view = self.env.ref("budget_control.view_account_analytic_account_form").id
        return {
            "name": _("Analytic Accounts"),
            "type": "ir.actions.act_window",
            "res_model": "account.analytic.account",
            "views": [[list_view, "list"], [form_view, "form"]],
            "view_mode": "list",
            "context": self.env.context,
            "domain": domain,
        }

    def button_open_allocation(self):
        self.ensure_one()
        context = self.env.context.copy()
        context["active_test"] = False
        domain = self._get_domain_open_allocation()
        return {
            "name": _("Budget Allocation Line"),
            "type": "ir.actions.act_window",
            "res_model": "budget.allocation.line",
            "view_mode": "tree",
            "context": context,
            "domain": domain,
        }

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
    _rec_name = "id"  # For unique ref
    _check_company_auto = True

    budget_allocation_id = fields.Many2one(
        comodel_name="budget.allocation",
        string="Budget Allocation",
        ondelete="cascade",
        required=True,
        readonly=True,
        index=True,
        check_company=True,
    )
    budget_period_id = fields.Many2one(
        comodel_name="budget.period",
        related="budget_allocation_id.budget_period_id",
        store=True,
        index=True,
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
        index=True,
    )
    name = fields.Char(string="Description")
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        required=True,
        index=True,
    )
    estimated_amount = fields.Monetary(
        compute="_compute_estimated_amount",
        store=True,
        readonly=False,
        help="Estimated amount to be received this year",
    )
    allocated_amount = fields.Monetary(
        string="Allocated",
        help="Initial allocated amount",
    )
    released_amount = fields.Monetary(
        string="Released",
        help="Total current amount",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.user.company_id,
        required=False,
        index=True,
        string="Company",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency", related="company_id.currency_id"
    )
    active = fields.Boolean(related="budget_allocation_id.active")

    @api.depends("allocated_amount")
    def _compute_estimated_amount(self):
        for rec in self:
            rec.estimated_amount = rec.estimated_amount or rec.allocated_amount
