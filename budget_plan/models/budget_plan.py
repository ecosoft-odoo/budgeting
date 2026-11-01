# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from collections import defaultdict

from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, format_amount

from odoo.addons.budget_control.models.analytic_plan import BUDGET_COLUMN


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

    def write(self, vals):
        # The allocations of consumed analytic accounts stay in their period
        lines = self.line_ids.filtered("detail_ids")
        if "budget_period_id" in vals:
            lines.filtered(
                lambda line: line.budget_period_id.id != vals["budget_period_id"]
            )._check_details_kept(moving=True)
        res = super().write(vals)
        if "budget_period_id" in vals:
            lines._check_detail_consumptions()
        if "company_ids" in vals:
            lines._check_detail_dimensions()
        return res

    @api.constrains("budget_period_id")
    def _check_fiscal_budget_period(self):
        if self.filtered(lambda plan: plan.budget_period_id.budget_scope != "fiscal"):
            raise ValidationError(
                self.env._(
                    "Budget Plans use Fiscal Periods. Lifetime budgets are managed "
                    "directly from their Analytic Budget Control."
                )
            )

    def _is_control_shared(self, control):
        """Whether ``control`` serves the companies of this plan that may use
        its analytic account."""
        self.ensure_one()
        companies = self.company_ids
        analytic_company = control.analytic_account_id.company_id
        if analytic_company:
            companies = companies.filtered(
                lambda company: analytic_company in company.parent_ids
            )
        return all(control._is_company_allowed(company) for company in companies)

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
            # A shared analytic is shared by the companies of the plan
            | ({} if x.company_id else {"company_ids": self.company_ids.ids})
            for x in analytic_plan
        ]

    def _create_budget_controls(self, vals):
        return self.env["budget.control"].create(vals)

    def _update_budget_control_values(self):
        plan_line = self.line_ids.with_context(active_test=False)
        dp = self.currency_id.decimal_places
        for line in plan_line:
            budget_control = line.budget_control_ids.filtered(
                lambda control, line=line: (
                    control.active and control.budget_period_id == line.budget_period_id
                )
            )
            if not budget_control:
                budget_control = line.budget_control_ids.filtered(
                    lambda control, line=line: (
                        control.budget_period_id == line.budget_period_id
                    )
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
        period = self.budget_period_id
        if not period.template_id or not period.plan_date_range_type_id:
            raise UserError(
                self.env._(
                    "Set the Budget Template and Plan Date Range of Budget Period "
                    "%(period)s first.",
                    period=period.display_name,
                )
            )
        self.line_ids._check_fiscal_analytic_account()
        self.line_ids._check_details_allocated()
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
                lambda control: (
                    not control.budget_plan_id or control.budget_plan_id == self
                )
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

        not_shared = target_controls.filtered(
            lambda control: not self._is_control_shared(control)
        )
        if not_shared:
            raise UserError(
                self.env._(
                    "Budget Control %(controls)s is not shared with all the "
                    "companies of Budget Plan %(plan)s.",
                    controls=", ".join(not_shared.mapped("display_name")),
                    plan=self.display_name,
                )
            )
        unowned_controls = target_controls.filtered(
            lambda control: not control.budget_plan_id
        )
        # Updating the allocation sets a sheet back to draft
        started_controls = unowned_controls.filtered(
            lambda control: control.state in ("submit", "done")
        )
        if started_controls:
            raise UserError(
                self.env._(
                    "Set Budget Control %(controls)s to draft before Budget Plan "
                    "%(plan)s manages it.",
                    controls=", ".join(started_controls.mapped("display_name")),
                    plan=self.display_name,
                )
            )
        unowned_controls.write({"budget_plan_id": self.id})
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
                lambda control, line=line: (
                    control.active and control.budget_period_id == line.budget_period_id
                )
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
                        "%s has amount less than consumed.",
                        line.analytic_account_id.display_name,
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
                    lambda control, line=line: (
                        control.active
                        and control.budget_period_id == line.budget_period_id
                    )
                )
                if not active_control:
                    continue

                if len(active_control) > 1:
                    raise UserError(
                        self.env._(
                            "%s should have only 1 active budget control",
                            line.analytic_account_id.display_name,
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
        """Analytics the plan budgets: the yearly ones of its period, and those
        without Budget Period open in it, dated or budgeted in the previous
        period, i.e. continuing."""
        self.ensure_one()
        previous = (
            self.env["budget.control"]
            .sudo()
            .search(
                [
                    (
                        "budget_period_id.bm_date_to",
                        "=",
                        fields.Date.subtract(self.date_from, days=1),
                    ),
                    ("active", "=", True),
                    ("state", "!=", "cancel"),
                ]
            )
            .analytic_account_id
        )
        domain = [
            ("budget_control_scope", "=", "fiscal"),
            ("root_plan_id.control_budget", "=", True),
            "|",
            ("budget_period_id", "=", self.budget_period_id.id),
            "&",
            "&",
            "&",
            ("budget_period_id", "=", False),
            "|",
            ("bm_date_from", "=", False),
            ("bm_date_from", "<=", self.date_to),
            "|",
            ("bm_date_to", "=", False),
            ("bm_date_to", ">=", self.date_from),
            "|",
            ("id", "in", previous.ids),
            "&",
            ("bm_date_from", "!=", False),
            ("bm_date_to", "!=", False),
        ]
        if self.company_ids:
            domain += [
                "|",
                ("company_id", "=", False),
                ("company_id", "parent_of", self.company_ids.ids),
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
        self.line_ids._check_details_allocated()
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
        compute="_compute_allocated_amount",
        help="New Budget + Forward Balance available for allocation.",
    )
    released_amount = fields.Monetary(string="Released")
    amount = fields.Monetary(
        string="New Budget",
        compute="_compute_amount",
        store=True,
        readonly=False,
        help="Budget of the period, without the forward balance. With details, "
        "their sum less the forward balance when they change.",
    )
    amount_unallocated = fields.Monetary(
        string="Unallocated",
        compute="_compute_allocated_amount",
        help="Part of the allocated amount the details do not allocate, e.g. a "
        "forward balance completed after them.",
    )
    detail_ids = fields.One2many(
        comodel_name="budget.plan.line.detail",
        inverse_name="plan_line_id",
        string="Details",
        copy=True,
        help="Allocation of the line by dimension, e.g. by fund: the budget "
        "control sheet stays one for the analytic account.",
    )
    plan_state = fields.Selection(related="plan_id.state")
    amount_forward_in = fields.Monetary(
        string="Forward Balance",
        compute="_compute_amount_forward_in",
        help="Available budget carried in from a completed forward balance.",
    )
    amount_consumed = fields.Monetary(string="Consumed")
    company_ids = fields.Many2many(
        comodel_name="res.company", related="plan_id.company_ids"
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency", related="plan_id.currency_id"
    )
    active_status = fields.Boolean(
        default=True, help="Activate/Deactivate when create/Update Budget Control"
    )

    def write(self, vals):
        # The allocations of consumed analytic accounts stay with them
        self.filtered(
            lambda line: (
                line.detail_ids
                and any(
                    fname in vals and line[fname].id != vals[fname]
                    for fname in ("analytic_account_id", "plan_id")
                )
            )
        )._check_details_kept(moving=True)
        # Details are checked together, once all are written
        allocated = self.filtered("detail_ids") if "detail_ids" in vals else self
        lines = self.with_context(budget_plan_line_details="detail_ids" in vals)
        res = super(BudgetPlanLine, lines).write(vals)
        if "detail_ids" in vals:
            allocated.filtered(lambda line: not line.detail_ids)._check_details_kept()
        return res

    @api.constrains("detail_ids", "analytic_account_id", "plan_id")
    def _check_details(self):
        self._check_detail_dimensions()
        self._check_detail_consumptions()

    def _get_budget_mandatory_fnames(self):
        """Plan columns each detail of the line needs: those of the plans
        mandatory in budget plans (Applicability) for the company of its
        analytic account, else for a company of its plan."""
        self.ensure_one()
        Detail = self.env["budget.plan.line.detail"]
        Plan = self.env["account.analytic.plan"]
        companies = (
            self.analytic_account_id.company_id
            or self.plan_id.company_ids
            or self.env.company
        )
        return [
            fname
            for fname in Detail._get_budget_plan_fnames()
            if any(
                Plan.browse(
                    int(BUDGET_COLUMN.fullmatch(fname).group(1))
                )._get_applicability(business_domain="budget", company_id=company.id)
                == "mandatory"
                for company in companies
            )
        ]

    def _check_detail_dimensions(self):
        """The details of a line hold the accounts of the plans of their
        columns, those of mandatory plans, and each combination once. A detail
        without an account of a plan matches the documents without one."""
        Detail = self.env["budget.plan.line.detail"]
        for line in self.filtered("detail_ids"):
            details = line.detail_ids
            misplaced = [
                f"- {detail[fname].display_name}: {Detail._fields[fname].string}"
                for detail in details
                for fname in Detail._get_budget_plan_fnames()
                if detail[fname]
                and detail[fname].root_plan_id.id
                != int(BUDGET_COLUMN.fullmatch(fname).group(1))
            ]
            if misplaced:
                raise ValidationError(
                    self.env._(
                        "Accounts outside the column of their plan in the details "
                        "of %(analytic)s:\n%(accounts)s",
                        analytic=line.analytic_account_id.display_name,
                        accounts="\n".join(misplaced),
                    )
                )
            required = line._get_budget_mandatory_fnames()
            fnames = details._get_dimension_fnames()
            missing = []
            for detail in details:
                plans = [
                    Detail._fields[fname].string
                    for fname in required
                    if not detail[fname]
                ]
                if plans:
                    name = Detail._get_dimensions_name(detail._get_dimensions(fnames))
                    missing.append(f"- {name}: {', '.join(plans)}")
            if missing:
                raise ValidationError(
                    self.env._(
                        "Mandatory plans missing in the details of %(analytic)s:\n"
                        "%(missing)s",
                        analytic=line.analytic_account_id.display_name,
                        missing="\n".join(missing),
                    )
                )
            keys = set()
            for detail in details:
                key = detail._get_dimensions(fnames)
                if key in keys:
                    raise ValidationError(
                        self.env._(
                            "Duplicate allocation found: %s",
                            Detail._get_budget_name(line.analytic_account_id, key),
                        )
                    )
                keys.add(key)

    def unlink(self):
        # The details go with their line
        self.filtered("detail_ids")._check_details_kept()
        return super().unlink()

    def _check_details_kept(self, moving=False):
        """Lines whose details are all removed, or ``moving`` to another
        analytic account or period, stop allocating their analytic account,
        unless it is consumed in the period that controls its allocations."""
        Detail = self.env["budget.plan.line.detail"]
        lines = self.filtered(lambda line: line.budget_period_id.control_allocation)
        for line in lines:
            consumed = -Detail._get_budget_consumptions(
                line.budget_period_id, line.analytic_account_id, ()
            ).get((), 0.0)
            currency = line.currency_id or self.env.company.currency_id
            if float_compare(consumed, 0.0, precision_rounding=currency.rounding) <= 0:
                continue
            vals = {
                "analytic": line.analytic_account_id.display_name,
                "consumed": format_amount(self.env, consumed, currency),
                "period": line.budget_period_id.display_name,
            }
            if moving:
                raise ValidationError(
                    self.env._(
                        "Cannot move the details of %(analytic)s: %(consumed)s is "
                        "already committed or spent in %(period)s.",
                        **vals,
                    )
                )
            raise ValidationError(
                self.env._(
                    "Cannot remove all the details of %(analytic)s: %(consumed)s "
                    "is already committed or spent in %(period)s.",
                    **vals,
                )
            )

    def _check_detail_consumptions(self):
        """The details of a line cover the commitments and actuals of its
        analytic account in the period, by their dimensions, when the period
        controls its allocations."""
        Detail = self.env["budget.plan.line.detail"]
        lines = self.filtered(
            lambda line: line.detail_ids and line.budget_period_id.control_allocation
        )
        for line in lines:
            details = line.detail_ids
            fnames = details._get_dimension_fnames()
            allocated = defaultdict(float)
            for detail in details:
                allocated[detail._get_dimensions(fnames)] += detail.amount
            consumptions = Detail._get_budget_consumptions(
                line.budget_period_id, line.analytic_account_id, fnames
            )
            currency = line.currency_id or self.env.company.currency_id
            for dimensions, amount in sorted(consumptions.items()):
                consumed = -amount
                if (
                    float_compare(consumed, 0.0, precision_rounding=currency.rounding)
                    <= 0
                ):
                    continue
                vals = {
                    "budget": Detail._get_budget_name(
                        line.analytic_account_id, dimensions
                    ),
                    "consumed": format_amount(self.env, consumed, currency),
                    "period": line.budget_period_id.display_name,
                }
                if dimensions not in allocated:
                    raise ValidationError(
                        self.env._(
                            "Keep a detail for %(budget)s: %(consumed)s is already "
                            "committed or spent on it in %(period)s.",
                            **vals,
                        )
                    )
                if (
                    float_compare(
                        allocated[dimensions],
                        consumed,
                        precision_rounding=currency.rounding,
                    )
                    < 0
                ):
                    raise ValidationError(
                        self.env._(
                            "%(budget)s cannot be allocated less than %(consumed)s, "
                            "already committed or spent in %(period)s.",
                            **vals,
                        )
                    )

    @api.depends("detail_ids.amount")
    def _compute_amount(self):
        # The details allocate the forward balance too: one completed after
        # them is left unallocated, and does not change the new budget
        for rec in self.filtered("detail_ids"):
            rec.amount = max(
                sum(rec.detail_ids.mapped("amount")) - rec.amount_forward_in, 0.0
            )

    def _check_details_allocated(self):
        """The details of a line, if any, allocate all its allocated amount."""
        for line in self.filtered("detail_ids"):
            currency = line.currency_id or self.env.company.currency_id
            if not currency.is_zero(line.amount_unallocated):
                raise UserError(
                    self.env._(
                        "The details of %(analytic)s leave %(amount)s unallocated: "
                        "allocate its New Budget and Forward Balance.",
                        analytic=line.analytic_account_id.display_name,
                        amount=format_amount(
                            self.env, line.amount_unallocated, currency
                        ),
                    )
                )

    def action_open_details(self):
        """Allocate the line by dimension, e.g. by fund."""
        self.ensure_one()
        return {
            "name": self.env._("Details of %s", self.analytic_account_id.display_name),
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "views": [
                (
                    self.env.ref("budget_plan.view_budget_plan_line_detail_form").id,
                    "form",
                )
            ],
            "target": "new",
        }

    @api.depends("analytic_account_id", "budget_period_id")
    def _compute_amount_forward_in(self):
        period_ids = self.mapped("budget_period_id").ids
        analytic_ids = self.mapped("analytic_account_id").ids
        amounts = self.env["budget.balance.forward.line"]._get_forward_balance_map(
            period_ids, analytic_ids
        )
        for rec in self:
            rec.amount_forward_in = amounts[
                (rec.budget_period_id.id, rec.analytic_account_id.id)
            ]

    @api.depends("amount", "amount_forward_in", "detail_ids.amount")
    def _compute_allocated_amount(self):
        for rec in self:
            rec.allocated_amount = rec.amount + rec.amount_forward_in
            rec.amount_unallocated = (
                rec.allocated_amount - sum(rec.detail_ids.mapped("amount"))
                if rec.detail_ids
                else 0.0
            )

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
    def _check_analytic_control_budget(self):
        self.analytic_account_id._check_control_budget_plan()

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

        # Lines may belong to several plans, e.g. when copying plans
        duplicates = self.env["budget.plan.line"]._read_group(
            [
                ("analytic_account_id", "in", self.analytic_account_id.ids),
                ("plan_id", "in", self.plan_id.ids),
            ],
            ["plan_id", "analytic_account_id"],
            having=[("__count", ">", 1)],
        )
        if duplicates:
            raise UserError(
                self.env._(
                    "Duplicate analytic account found: %s",
                    ", ".join(
                        sorted(
                            {analytic.display_name for _plan, analytic in duplicates}
                        )
                    ),
                )
            )
