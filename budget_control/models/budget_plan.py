# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class BudgetPlan(models.Model):
    _name = "budget.plan"
    _description = "Budget Plan"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        required=True,
        tracking=True,
    )
    budget_period_id = fields.Many2one(
        comodel_name="budget.period",
        required=True,
        domain=[("budget_scope", "=", "fiscal")],
    )
    date_from = fields.Date(related="budget_period_id.bm_date_from")
    date_to = fields.Date(related="budget_period_id.bm_date_to")
    budget_control_ids = fields.One2many(
        comodel_name="budget.control",
        inverse_name="budget_plan_id",
        context={"active_test": False},
    )
    budget_control_count = fields.Integer(
        string="# of Budget Control",
        compute="_compute_budget_control_count",
        help="Count budget control in Plan",
    )
    total_amount = fields.Monetary(compute="_compute_total_amount")
    company_ids = fields.Many2many(
        comodel_name="res.company",
        relation="budget_plan_company_rel",
        column1="budget_plan_id",
        column2="company_id",
        string="Companies",
        default=lambda self: self.env.context.get("allowed_company_ids"),
        tracking=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency", compute="_compute_currency_id"
    )
    line_ids = fields.One2many(
        comodel_name="budget.plan.line",
        inverse_name="plan_id",
        copy=True,
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
        string="Status",
        default="draft",
        tracking=True,
    )

    @api.constrains("budget_period_id")
    def _check_fiscal_budget_period(self):
        if self.filtered(lambda plan: plan.budget_period_id.budget_scope != "fiscal"):
            raise ValidationError(
                self.env._(
                    "Budget Plans use Fiscal Periods. Lifetime budgets are managed "
                    "directly from their Analytic Budget Control."
                )
            )

    @api.depends("company_ids")
    def _compute_currency_id(self):
        for rec in self:
            currencies = rec.company_ids.mapped(
                "currency_id"
            )  # Get all currencies from companies
            unique_currencies = set(currencies.ids)  # Get unique currency IDs
            if len(unique_currencies) > 1:
                raise UserError(
                    self.env._("Selected companies have different currencies!")
                )

            rec.currency_id = next(iter(currencies), self.env.company.currency_id)

    @api.depends(
        "line_ids.amount",
        "line_ids.amount_forward_in",
        "line_ids.allocated_amount",
        "line_ids.analytic_account_id",
        "budget_period_id",
    )
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped("allocated_amount"))

    @api.depends("budget_control_ids")
    def _compute_budget_control_count(self):
        for rec in self:
            rec.budget_control_count = len(rec.budget_control_ids)

    def button_open_budget_control(self):
        self.ensure_one()
        # Get budget controls in one query with proper context
        budget_controls = self.with_context(
            create=False,
            active_test=False,
            search_default_current_period=False,
        ).budget_control_ids

        action = {
            "name": self.env._("Budget Control Sheet"),
            "type": "ir.actions.act_window",
            "res_model": "budget.control",
            "view_mode": "list,form",
            "domain": [("id", "in", budget_controls.ids)],
        }
        return action

    def _prepare_budget_control_sheet(self, analytic_plan, **kwargs):
        self.ensure_one()
        plan_date_range_id = self.budget_period_id.plan_date_range_type_id.id
        currency_id = self.currency_id.id
        budget_period = self.budget_period_id
        # Additional params
        template_lines = kwargs.get("template_lines", [])
        use_all_kpis = kwargs.get("use_all_kpis", False)
        return [
            {
                "analytic_account_id": x.id,
                "name": f"{budget_period.name} :: {x.name}",
                "plan_date_range_type_id": plan_date_range_id,
                "use_all_kpis": use_all_kpis,
                "template_line_ids": template_lines,
                "budget_period_id": budget_period.id,
                "currency_id": currency_id,
                "budget_plan_id": self.id,
            }
            for x in analytic_plan
        ]

    def _create_budget_controls(self, vals):
        return self.env["budget.control"].create(vals)

    def _update_budget_control_values(self):
        plan_line = self.line_ids.with_context(active_test=False)
        dp = self.currency_id.decimal_places
        for line in plan_line:
            budget_control = line.budget_control_ids.filtered(
                lambda control, line=line: control.active
                and control.budget_period_id == line.budget_period_id
            )
            if not budget_control:
                budget_control = line.budget_control_ids.filtered(
                    lambda control, line=line: control.budget_period_id
                    == line.budget_period_id
                ).sorted("id")[-1:]
            if not budget_control:
                continue
            if (
                float_compare(
                    budget_control.allocated_amount,
                    line.allocated_amount,
                    precision_digits=dp,
                )
                != 0
                or budget_control.active != line.active_status
            ):
                budget_control.action_draft()
                budget_control.write(
                    {
                        "allocated_amount": line.allocated_amount,
                        "active": line.active_status,
                    }
                )
        return True

    def action_create_update_budget_control(self):
        self.ensure_one()
        self.line_ids._check_fiscal_analytic_account()
        analytic_plan = self.line_ids.mapped("analytic_account_id")
        # A budget control is unique in the scope of a budget period and an
        # analytic account.  The same analytic may legitimately have a budget
        # control in every year (Extend carry-forward).
        existing_budget_controls = (
            self.env["budget.control"]
            .with_context(active_test=False)
            .search(
                [
                    ("budget_period_id", "=", self.budget_period_id.id),
                    ("analytic_account_id", "in", analytic_plan.ids),
                ]
            )
        )
        controls_by_analytic = {}
        for control in existing_budget_controls.sorted("id"):
            controls_by_analytic.setdefault(
                control.analytic_account_id.id, self.env["budget.control"]
            )
            controls_by_analytic[control.analytic_account_id.id] |= control

        target_controls = self.env["budget.control"]
        conflicting_controls = self.env["budget.control"]
        for analytic in analytic_plan:
            candidates = controls_by_analytic.get(
                analytic.id, self.env["budget.control"]
            )
            active_control = candidates.filtered(
                lambda control: control.active and control.state != "cancel"
            )[-1:]
            if (
                active_control
                and active_control.budget_plan_id
                and active_control.budget_plan_id != self
            ):
                conflicting_controls |= active_control
                continue
            if active_control:
                target_controls |= active_control
                continue
            reusable_control = candidates.filtered(
                lambda control: not control.budget_plan_id
                or control.budget_plan_id == self
            )[-1:]
            target_controls |= reusable_control

        if conflicting_controls:
            plan_names = ", ".join(
                conflicting_controls.mapped("budget_plan_id.display_name")
            )
            analytic_names = ", ".join(
                conflicting_controls.mapped("analytic_account_id.display_name")
            )
            raise UserError(
                self.env._(
                    "Budget Control for %(analytics)s is already managed by "
                    "another Budget Plan: %(plans)s.",
                    analytics=analytic_names,
                    plans=plan_names,
                )
            )

        target_controls.filtered(lambda control: not control.budget_plan_id).write(
            {"budget_plan_id": self.id}
        )
        existing_analytics = target_controls.mapped("analytic_account_id")
        new_analytic = analytic_plan - existing_analytics

        # Create new budget control if new plan line is added
        if new_analytic:
            # Prepare budget control
            value_bc = self._prepare_budget_control_sheet(new_analytic)
            # Create budget controls that are not already exists
            new_budget_controls = self._create_budget_controls(value_bc)

            new_budget_controls.prepare_budget_control_matrix()

        # Update budget control values
        self._update_budget_control_values()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": self.env._("Budget Control has been updated!"),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def check_plan_consumed(self):
        prec_digits = self.currency_id.decimal_places
        for line in self.mapped("line_ids"):
            amount = line.allocated_amount
            active_controls = line.budget_control_ids.filtered(
                lambda control, line=line: control.active
                and control.budget_period_id == line.budget_period_id
            )
            transferred_amount = sum(active_controls.mapped("transferred_amount"))
            released_amount = amount + transferred_amount
            # Check allocated + transfers against the amount already consumed.
            if (
                float_compare(
                    released_amount,
                    line.amount_consumed,
                    precision_digits=prec_digits,
                )
                == -1
            ):
                raise UserError(
                    self.env._(
                        f"{line.analytic_account_id.display_name} "
                        f"has amount less than consumed."
                    )
                )
            # Released is allocated plus the current transfers. Allocated is
            # computed directly from New Budget + Forward Balance.
            if line.released_amount != released_amount:
                line.released_amount = released_amount

    def action_update_amount_consumed(self):
        """Update amount consumed and released from budget control"""
        for rec in self:
            for line in rec.line_ids:
                # find consumed amount from budget control
                active_control = line.budget_control_ids.filtered(
                    lambda control, line=line: control.active
                    and control.budget_period_id == line.budget_period_id
                )
                if not active_control:
                    continue

                if len(active_control) > 1:
                    raise UserError(
                        self.env._(
                            f"{line.analytic_account_id.display_name} should have "
                            f"only 1 active budget control"
                        )
                    )
                line.amount_consumed = active_control.amount_consumed
                line.released_amount = active_control.released_amount

    def _prepare_update_plan_lines(self, analytics):
        self.ensure_one()
        if not analytics:
            return []
        active_controls = self.env["budget.control"].search(
            [
                ("analytic_account_id", "in", analytics.ids),
                ("budget_period_id", "=", self.budget_period_id.id),
                ("active", "=", True),
            ],
            order="id",
        )
        controls_by_analytic = {
            control.analytic_account_id.id: control for control in active_controls
        }
        empty_control = self.env["budget.control"]
        lines = []
        for analytic in analytics:
            active_control = controls_by_analytic.get(analytic.id, empty_control)
            lines.append(
                Command.create(
                    {
                        "analytic_account_id": analytic.id,
                        "amount_consumed": active_control.amount_consumed,
                        "released_amount": active_control.released_amount,
                    }
                )
            )
        return lines

    def _get_eligible_analytic_domain(self):
        self.ensure_one()
        domain = [
            ("budget_control_scope", "=", "fiscal"),
            ("bm_date_from", "<=", self.date_to),
            ("bm_date_to", ">=", self.date_from),
        ]
        if self.company_ids:
            domain += [
                "|",
                ("budget_company_ids", "in", self.company_ids.ids),
                ("budget_company_ids", "=", False),
            ]
        return domain

    def action_update_plan(self):
        """Update plan line is not in plan line"""
        Analytic = self.env["account.analytic.account"]

        self.mapped("line_ids")._check_fiscal_analytic_account()
        for rec in self:
            existing_analytic_ids = rec.line_ids.analytic_account_id.ids
            domain = rec._get_eligible_analytic_domain()
            if existing_analytic_ids:
                domain.append(("id", "not in", existing_analytic_ids))

            new_analytics = Analytic.search(domain)

            lines = rec._prepare_update_plan_lines(new_analytics)
            if lines:
                rec.write({"line_ids": lines})

    def _get_context_plan_analytic(self):
        ctx = self.env.context.copy()
        ctx["default_company_ids"] = self.company_ids.ids
        return ctx

    def action_get_all_analytic_accounts(self):
        ctx = self._get_context_plan_analytic()
        return {
            "name": self.env._("Analytic Account"),
            "type": "ir.actions.act_window",
            "res_model": "budget.plan.analytic.select",
            "view_mode": "form",
            "target": "new",
            "context": ctx,
        }

    def action_confirm(self):
        # Update amount consumed and released
        self.action_update_amount_consumed()
        # Update plan line
        self.action_update_plan()
        # Check plan consumed
        self.check_plan_consumed()
        return self.write({"state": "confirm"})

    def action_done(self):
        return self.write({"state": "done"})

    def action_cancel(self):
        return self.write({"state": "cancel"})

    def action_draft(self):
        return self.write({"state": "draft"})


class BudgetPlanLine(models.Model):
    _name = "budget.plan.line"
    _description = "Budget Plan Line"
    _check_company_auto = True

    plan_id = fields.Many2one(
        comodel_name="budget.plan",
        index=True,
        ondelete="cascade",
    )
    budget_control_ids = fields.Many2many(
        comodel_name="budget.control",
        string="Related Budget Control(s)",
        compute="_compute_budget_control_ids",
        help="Note: It is intention for this field to compute in realtime",
    )
    budget_period_id = fields.Many2one(
        comodel_name="budget.period", related="plan_id.budget_period_id"
    )
    date_from = fields.Date(related="plan_id.date_from")
    date_to = fields.Date(related="plan_id.date_to")
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        required=True,
    )
    allocated_amount = fields.Monetary(
        string="Allocated",
        compute="_compute_budget_amounts",
        help="New Budget + Forward Balance available for allocation.",
    )
    released_amount = fields.Monetary(string="Released")
    amount = fields.Monetary(string="New Budget")
    amount_forward_in = fields.Monetary(
        string="Forward Balance",
        compute="_compute_budget_amounts",
        help="Available budget carried in from a completed forward balance.",
    )
    amount_consumed = fields.Monetary(string="Consumed")
    company_ids = fields.Many2many(
        comodel_name="res.company", related="analytic_account_id.budget_company_ids"
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency", related="plan_id.currency_id"
    )
    active_status = fields.Boolean(
        default=True, help="Activate/Deactivate when create/Update Budget Control"
    )

    @api.depends("amount", "analytic_account_id", "budget_period_id")
    def _compute_budget_amounts(self):
        """Compute the forward balance and the total amount to allocate."""
        period_ids = self.mapped("budget_period_id").ids
        analytic_ids = self.mapped("analytic_account_id").ids
        amounts = self.env["budget.balance.forward.line"]._get_forward_balance_map(
            period_ids, analytic_ids
        )
        for rec in self:
            rec.amount_forward_in = amounts[
                (rec.budget_period_id.id, rec.analytic_account_id.id)
            ]
            rec.allocated_amount = rec.amount + rec.amount_forward_in

    @api.constrains("amount")
    def _check_amount_nonnegative(self):
        for rec in self:
            if (
                float_compare(
                    rec.amount,
                    0.0,
                    precision_rounding=rec.currency_id.rounding,
                )
                < 0
            ):
                raise ValidationError(self.env._("New Budget cannot be negative."))

    @api.constrains("analytic_account_id")
    def _check_fiscal_analytic_account(self):
        invalid_lines = self.filtered(
            lambda line: line.analytic_account_id.budget_control_scope != "fiscal"
        )
        if invalid_lines:
            analytic_names = ", ".join(
                sorted(set(invalid_lines.mapped("analytic_account_id.display_name")))
            )
            raise ValidationError(
                self.env._(
                    "Budget Plan lines can use only Fiscal analytics. Manage the "
                    "following Lifetime analytics directly from their Budget "
                    "Controls: %(analytics)s.",
                    analytics=analytic_names,
                )
            )

    @api.depends(
        "analytic_account_id.budget_control_ids.budget_plan_id",
        "plan_id",
    )
    def _compute_budget_control_ids(self):
        for rec in self.sudo():
            rec.budget_control_ids = (
                rec.analytic_account_id.budget_control_ids.filtered(
                    lambda control, rec=rec: control.budget_plan_id == rec.plan_id
                )
            )

    @api.constrains("analytic_account_id")
    def _check_duplicate_analytic_account(self):
        if not self:
            return

        PlanLine = self.env["budget.plan.line"]
        analytic_ids = self.mapped("analytic_account_id.id")

        # Group by analytic_account_id and count occurrences
        duplicates = PlanLine.read_group(
            [
                ("analytic_account_id", "in", analytic_ids),
                ("plan_id", "=", self.plan_id.id),
            ],
            ["analytic_account_id"],
            ["analytic_account_id"],
        )

        # Check for duplicates
        duplicate_analytics = {
            dup["analytic_account_id"][1]
            for dup in duplicates
            if dup["analytic_account_id_count"] > 1
        }
        if duplicate_analytics:
            raise UserError(
                self.env._(f"Duplicate analytic account found: {duplicate_analytics}")
            )
