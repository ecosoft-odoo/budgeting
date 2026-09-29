# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from json import dumps

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
        states={"draft": [("readonly", "=", False)]},
    )
    plan_id = fields.Many2one(
        comodel_name="budget.plan",
        index=True,
        copy=False,
    )
    allocated_amount = fields.Monetary(
        compute="_compute_allocated_amount", help="Sum of amount allocation"
    )
    line_ids = fields.One2many(
        comodel_name="budget.allocation.line",
        inverse_name="budget_allocation_id",
        copy=True,
        readonly=True,
        states={"draft": [("readonly", "=", False)]},
        context={"active_test": False},
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.user.company_id,
        required=True,
        readonly=True,
        states={"draft": [("readonly", "=", False)]},
    )
    amount_basis = fields.Selection(
        selection=[
            ("new_budget", "New Budget"),
            ("allocated", "Allocated"),
        ],
        string="Applied Amount Basis",
        required=True,
        readonly=True,
        copy=True,
        default=lambda self: self.env.user.company_id.budget_allocation_amount_basis,
        help="Company policy applied the last time this allocation was sent "
        "to its budget plan.",
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

    _sql_constraints = [
        (
            "budget_period_uniq",
            "UNIQUE(budget_period_id)",
            "Budget period must be unique!",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "amount_basis" not in vals:
                company = self.env["res.company"].browse(
                    vals.get("company_id") or self.env.user.company_id.id
                )
                vals["amount_basis"] = company.budget_allocation_amount_basis
        return super().create(vals_list)

    @api.depends("line_ids.allocated_amount")
    def _compute_allocated_amount(self):
        for rec in self:
            rec.allocated_amount = sum(rec.line_ids.mapped("allocated_amount"))

    def _prepare_vals_budget_plan(self):
        vals = {
            "name": self.name,
            "budget_period_id": self.budget_period_id.id,
            "budget_allocation_id": self.id,
            "init_amount": self.allocated_amount,
            "company_id": self.company_id.id,
        }
        return vals

    def update_amount_plan(self, budget_plan):
        self.ensure_one()
        budget_plan.action_update_plan()  # update plan lines
        amounts_by_analytic = {}
        for allocation_line in self.line_ids:
            analytic_id = allocation_line.analytic_account_id.id
            amounts_by_analytic[analytic_id] = (
                amounts_by_analytic.get(analytic_id, 0.0)
                + allocation_line.allocated_amount
            )
        for plan_line in budget_plan.line_ids:
            analytic_id = plan_line.analytic_account_id.id
            target = amounts_by_analytic.get(analytic_id, 0.0)
            if self.amount_basis == "allocated" and analytic_id in amounts_by_analytic:
                # Allocated = New Budget + both forwarded amounts.
                target -= plan_line.amount_forward_in + plan_line.amount_forward_commit
            # A line without allocation keeps its forwards with New Budget = 0.
            plan_line.amount = target

    def action_done(self):
        BudgetPlan = self.env["budget.plan"]
        for rec in self:
            # Read the current company policy when Done is pressed. An allocation
            # may have been created before the policy was changed in Settings.
            rec.amount_basis = rec.company_id.budget_allocation_amount_basis
            budget_plan = rec.plan_id
            # Create budget plan from allocation, if not created
            if not budget_plan:
                vals = rec._prepare_vals_budget_plan()
                budget_plan = BudgetPlan.create(vals)
                # Link allocation and budget plan
                rec.write({"plan_id": budget_plan.id})
            elif budget_plan.budget_allocation_id != rec:
                # A copied plan revision still points to the previous allocation.
                budget_plan.budget_allocation_id = rec
            # Write initial amount on budget plan
            budget_plan.write({"init_amount": rec.allocated_amount})
            # Update amount from allocation to budget plan lines
            rec.update_amount_plan(budget_plan)
            budget_plan._check_amount_negative()
            budget_plan._check_amount_initial()
            # Update released amount following allocated amount
            allocation_lines = rec.line_ids.filtered(
                lambda l: l.allocated_amount != l.released_amount
            )
            for line in allocation_lines:
                line.write({"released_amount": line.allocated_amount})
        return self.write({"state": "done"})

    def action_draft(self):
        return self.write({"state": "draft"})

    def action_cancel(self):
        return self.write({"state": "cancel"})

    def _get_domain_open_analytic(self):
        self.ensure_one()
        return [
            ("bm_date_to", ">=", self.budget_period_id.bm_date_from),
            ("bm_date_from", "<=", self.budget_period_id.bm_date_to),
        ]

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
    _inherit = "analytic.dimension.line"
    _description = "Budget Allocation Line"
    _rec_name = "id"  # For unique ref
    _check_company_auto = True
    _analytic_tag_field_name = "analytic_tag_ids"

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
    analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        string="Analytic Tags",
    )
    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        required=True,
        index=True,
        ondelete="restrict",
    )
    fund_group_id = fields.Many2one(
        comodel_name="budget.source.fund.group",
        related="fund_id.fund_group_id",
        store=True,
    )
    estimated_amount = fields.Monetary(
        compute="_compute_estimated_amount",
        store=True,
        readonly=False,
        help="Estimated amount to be received this year",
    )
    allocated_amount = fields.Monetary(
        string="Allocated",
        help="Amount interpreted according to the allocation's Amount Basis.",
    )
    released_amount = fields.Monetary(
        string="Released",
        help="Total current amount",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.user.company_id,
        required=False,
        string="Company",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency", related="company_id.currency_id"
    )
    active = fields.Boolean(related="budget_allocation_id.active")
    json_budget_popover = fields.Char(
        compute="_compute_json_budget_popover",
        help="What this analytic will have available in the allocation's budget "
        "period, before any budget plan is created",
    )

    @api.depends("allocated_amount")
    def _compute_estimated_amount(self):
        for rec in self:
            rec.estimated_amount = rec.estimated_amount or rec.allocated_amount

    def _get_period_allocated_amount(self):
        """Total allocated to this analytic across the whole budget period.

        ``budget.allocation`` is unique per budget period (see its
        ``_sql_constraints``), so the period total is this document's own lines
        for the same analytic - no query needed, and it stays live while the
        user is still editing the lines. A cancelled document allocates nothing.
        """
        self.ensure_one()
        allocation = self.budget_allocation_id
        if allocation.state == "cancel":
            return 0.0
        siblings = allocation.line_ids.filtered(
            lambda line: line.analytic_account_id == self.analytic_account_id
        )
        return sum(siblings.mapped("allocated_amount"))

    @api.depends(
        "analytic_account_id",
        "budget_period_id",
        "budget_allocation_id.state",
        "budget_allocation_id.amount_basis",
        "budget_allocation_id.company_id.budget_allocation_amount_basis",
        "budget_allocation_id.line_ids.allocated_amount",
        "budget_allocation_id.line_ids.analytic_account_id",
    )
    def _compute_json_budget_popover(self):
        """Preview the plan amounts using this allocation's captured policy."""
        FloatConverter = self.env["ir.qweb.field.float"]
        period_ids = self.mapped("budget_period_id").ids
        analytic_ids = self.mapped("analytic_account_id").ids
        balances = self.env["budget.balance.forward.line"]._get_forward_balance_map(
            period_ids, analytic_ids
        )
        commits = self.env["budget.commit.forward.line"]._get_forward_commit_map(
            period_ids, analytic_ids
        )

        def to_html(amount):
            return FloatConverter.value_to_html(
                amount, {"decimal_precision": "Product Price"}
            )

        for rec in self:
            if not rec.analytic_account_id:
                rec.json_budget_popover = False
                continue
            key = (rec.budget_period_id.id, rec.analytic_account_id.id)
            forward_in = balances[key]
            forward_commit = commits[key]
            allocated = rec._get_period_allocated_amount()
            allocation = rec.budget_allocation_id
            basis = (
                allocation.company_id.budget_allocation_amount_basis
                if allocation.state == "draft"
                else allocation.amount_basis
            )
            if basis == "allocated" and allocation.state != "cancel":
                new_budget = allocated - forward_in - forward_commit
                total = allocated
            else:
                new_budget = allocated
                total = forward_in + forward_commit + allocated
            rec.json_budget_popover = dumps(
                {
                    "title": _("Budget Figure"),
                    "icon": "fa-info-circle",
                    "popoverTemplate": "budget_allocation.budgetAllocationPopOver",
                    "analytic": rec.analytic_account_id.display_name,
                    "period": rec.budget_period_id.display_name,
                    "forward_in": to_html(forward_in),
                    "forward_commit": to_html(forward_commit),
                    "new_budget": to_html(new_budget),
                    "total": to_html(total),
                }
            )
