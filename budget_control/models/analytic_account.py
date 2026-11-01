# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from collections import defaultdict

from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import frozendict


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"
    _rec_names_search = ("name", "code", "budget_period_id")

    control_budget = fields.Boolean(
        related="root_plan_id.control_budget",
        help="Accounts of plans with Control Budget have budgets.",
    )
    budget_period_id = fields.Many2one(
        comodel_name="budget.period",
    )
    budget_control_scope = fields.Selection(
        selection=[
            ("fiscal", "Fiscal Period"),
            ("lifetime", "Lifetime"),
        ],
        string="Budget Scope",
        required=True,
        default="fiscal",
        index=True,
        tracking=True,
        help="Fiscal analytics use the Budget Period matching each document date. "
        "Lifetime analytics use one dedicated period for their complete duration "
        "and do not reset at fiscal year end.",
    )
    budget_control_ids = fields.One2many(
        string="Budget Control(s)",
        comodel_name="budget.control",
        inverse_name="analytic_account_id",
        readonly=True,
    )
    next_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Continues As",
        copy=False,
        index="btree_not_null",
        tracking=True,
        domain="[('id', '!=', id), ('control_budget', '=', True), "
        "('budget_control_scope', '=', 'fiscal')]",
        help="Analytic the budgets and commitments of this one are carried "
        "forward to once it ends, e.g. the analytic of the next year of a yearly "
        "analytic. An analytic without Budget Period continues as itself while "
        "it is open.",
    )
    bm_date_from = fields.Date(
        string="Date From",
        compute="_compute_bm_date",
        store=True,
        readonly=False,
        tracking=True,
        help="Budget commit date must conform with this date",
    )
    bm_date_to = fields.Date(
        string="Date To",
        compute="_compute_bm_date",
        store=True,
        readonly=False,
        tracking=True,
        help="Budget commit date must conform with this date",
    )
    auto_adjust_date_commit = fields.Boolean(
        string="Auto Adjust Commit Date",
        default=True,
        help="Date From and Date To is used to determine valid date range of "
        "this analytic account when using with budgeting system. If this data range "
        "is setup, but the budget system set date_commit out of this date range "
        "it it can be adjusted automatically.",
    )
    amount_budget = fields.Monetary(
        string="Budgeted",
        compute="_compute_amount_budget_info",
        help="Sum of amount plan",
    )
    amount_forward_in = fields.Monetary(
        string="Forward In",
        compute="_compute_amount_budget_info",
        help="Available budget carried in from another budget period.",
    )
    amount_forward_out = fields.Monetary(
        string="Forward Out",
        compute="_compute_amount_budget_info",
        help="Available budget carried out, shown as a positive amount.",
    )
    amount_consumed = fields.Monetary(
        string="Consumed",
        compute="_compute_amount_budget_info",
        help="Consumed = Total Commitments + Actual",
    )
    amount_balance = fields.Monetary(
        string="Available",
        compute="_compute_amount_budget_info",
        help="Available = Total Budget - Forward Out - Consumed",
    )

    @api.depends("code", "partner_id", "budget_period_id")
    def _compute_display_name(self):
        res = super()._compute_display_name()
        for analytic in self:
            name = analytic.display_name
            if analytic.budget_period_id:
                name = f"{analytic.budget_period_id.name}: {name}"
            analytic.display_name = name
        return res

    @api.depends(
        "budget_period_id",
        "budget_period_id.bm_date_from",
        "budget_period_id.bm_date_to",
    )
    def _compute_bm_date(self):
        """Default effective date, but changable"""
        for rec in self:
            rec.bm_date_from = rec.budget_period_id.bm_date_from
            rec.bm_date_to = rec.budget_period_id.bm_date_to

    def _check_control_budget_plan(self):
        """Budgets can only be set on accounts of plans with Control Budget."""
        not_controlled = self.filtered(
            lambda analytic: not analytic.root_plan_id.control_budget
        )
        if not_controlled:
            raise ValidationError(
                self.env._(
                    "%s must belong to a plan with Control Budget ticked to have "
                    "a budget.",
                    ", ".join(not_controlled.mapped("display_name")),
                )
            )

    def write(self, vals):
        if "plan_id" in vals:
            # Budget moves keep the account in the column of its root plan
            root = self.env["account.analytic.plan"].browse(vals["plan_id"]).root_id
            moved = self.filtered(lambda analytic: analytic.root_plan_id != root)
            if moved:
                self.env["account.analytic.plan"]._check_budget_moves_unused(
                    moved,
                    self.env._(
                        "%s is used on budget moves, so it cannot move to "
                        "another root plan.",
                        moved[:1].display_name,
                    ),
                )
        res = super().write(vals)
        if "plan_id" in vals:
            self.env.transaction.invalidate_ormcache()
        return res

    def unlink(self):
        res = super().unlink()
        self.env.transaction.invalidate_ormcache()
        return res

    @api.model
    @api.ormcache("analytic_ids")
    def _get_analytic_control_budget(self, analytic_ids):
        """``{analytic_id: Control Budget of its root plan}`` for the accounts
        of ``analytic_ids`` (a sorted tuple) that exist: analytic distributions
        may keep deleted accounts."""
        analytics = self.sudo().browse(analytic_ids).exists()
        return frozendict(
            {
                analytic.id: analytic.root_plan_id.control_budget
                for analytic in analytics
            }
        )

    @api.constrains("plan_id")
    def _check_plan_control_budget(self):
        self.with_context(active_test=False).filtered(
            "budget_control_ids"
        )._check_control_budget_plan()

    @api.constrains("next_analytic_id")
    def _check_next_analytic(self):
        if self._has_cycle("next_analytic_id"):
            raise ValidationError(
                self.env._(
                    "An analytic cannot continue as itself, even through others."
                )
            )
        for analytic in self.filtered("next_analytic_id"):
            next_analytic = analytic.next_analytic_id
            if (
                not next_analytic.control_budget
                or next_analytic.budget_control_scope != "fiscal"
            ):
                raise ValidationError(
                    self.env._(
                        "%(analytic)s cannot continue as %(next)s: choose an "
                        "analytic of a plan with Control Budget and a Fiscal "
                        "scope.",
                        analytic=analytic.display_name,
                        next=next_analytic.display_name,
                    )
                )

    def _is_budget_open(self, date):
        """Whether this analytic takes commitments on ``date``."""
        self.ensure_one()
        return (not self.bm_date_from or self.bm_date_from <= date) and (
            not self.bm_date_to or self.bm_date_to >= date
        )

    def _is_forward_target(self, budget_period):
        """Whether budgets and commitments can be carried forward to this
        analytic in ``budget_period``: a fiscal analytic of a plan with Control
        Budget, of that period or of none, open when it starts."""
        self.ensure_one()
        return (
            self.control_budget
            and self.budget_control_scope == "fiscal"
            and (not self.budget_period_id or self.budget_period_id == budget_period)
            and self._is_budget_open(budget_period.bm_date_from)
        )

    def _get_forward_analytic(self, budget_period):
        """Analytic the budgets and commitments of this one are carried
        forward to in ``budget_period``: itself if it can take them, else the
        first analytic it continues as that can. None for Lifetime analytics,
        which keep them for their whole duration, or when none can."""
        self.ensure_one()
        if self.budget_control_scope == "lifetime":
            return self.browse()
        # No loop: see _check_next_analytic()
        analytic = self
        while analytic and not analytic._is_forward_target(budget_period):
            analytic = analytic.next_analytic_id
        return analytic

    def _extend_budget_analytic(self, budget_period):
        """Keep these analytics open to the end of ``budget_period``. Only
        analytics without Budget Period, i.e. continuing ones, have their own
        end date to extend."""
        yearly = self.filtered("budget_period_id")
        if yearly:
            raise UserError(
                self.env._(
                    "%s has a Budget Period: it continues as the analytic of the "
                    "next period instead of being extended.",
                    yearly[:1].display_name,
                )
            )
        for analytic in self.filtered("bm_date_to"):
            analytic.bm_date_to = max(analytic.bm_date_to, budget_period.bm_date_to)

    def _get_next_analytic_matches(self, budget_period):
        """Analytics that may be the one of ``budget_period`` this yearly
        analytic continues as: same name, code, root plan and company."""
        self.ensure_one()
        return self.search(
            [
                ("id", "!=", self.id),
                ("budget_period_id", "=", budget_period.id),
                ("name", "=", self.name),
                ("code", "=", self.code),
                ("root_plan_id", "=", self.root_plan_id.id),
                ("company_id", "=", self.company_id.id),
            ]
        )

    def _prepare_next_analytic_vals(self, budget_period):
        """Values of the copy of this yearly analytic for ``budget_period``."""
        self.ensure_one()
        # The dates of the analytic would be copied as they are
        return {
            "name": self.name,
            "budget_period_id": budget_period.id,
            "bm_date_from": budget_period.bm_date_from,
            "bm_date_to": budget_period.bm_date_to,
        }

    @api.constrains(
        "budget_control_scope",
        "budget_period_id",
    )
    def _check_budget_control_scope(self):
        for rec in self:
            active_controls = rec.budget_control_ids.filtered(
                lambda control: control.active and control.state != "cancel"
            )
            incompatible = active_controls.filtered(
                lambda control, rec=rec: (
                    control.budget_scope != rec.budget_control_scope
                    or (
                        rec.budget_control_scope == "lifetime"
                        and control.budget_period_id != rec.budget_period_id
                    )
                )
            )
            if incompatible:
                raise UserError(
                    self.env._(
                        "Archive or cancel incompatible Budget Control "
                        "%(control)s before changing the budget scope of analytic "
                        "%(analytic)s.",
                        control=incompatible[:1].display_name,
                        analytic=rec.display_name,
                    )
                )
        for rec in self.filtered(
            lambda analytic: analytic.budget_control_scope == "lifetime"
        ):
            if (
                not rec.budget_period_id
                or rec.budget_period_id.budget_scope != "lifetime"
            ):
                raise UserError(
                    self.env._(
                        "Lifetime analytic %(analytic)s needs its dedicated "
                        "Lifetime Budget Period.",
                        analytic=rec.display_name,
                    )
                )
            if rec not in rec.budget_period_id.control_analytic_account_ids:
                raise UserError(
                    self.env._(
                        "Lifetime Budget Period %(period)s must control "
                        "analytic %(analytic)s.",
                        period=rec.budget_period_id.display_name,
                        analytic=rec.display_name,
                    )
                )

    def _create_lifetime_budget_period(self, period_vals, reference_period=False):
        """Create and atomically assign one dedicated Lifetime period."""
        self.ensure_one()
        existing_period = self.budget_period_id.filtered(
            lambda period: period.budget_scope == "lifetime"
        )
        if self.budget_control_scope == "lifetime" or existing_period:
            raise UserError(
                self.env._(
                    "Analytic %(analytic)s already has a Lifetime Budget Period.",
                    analytic=self.display_name,
                )
            )

        active_controls = self.budget_control_ids.filtered(
            lambda control: control.active and control.state != "cancel"
        )
        if active_controls:
            raise UserError(
                self.env._(
                    "Archive or cancel Budget Control %(control)s before creating "
                    "a Lifetime budget for analytic %(analytic)s.",
                    control=active_controls[:1].display_name,
                    analytic=self.display_name,
                )
            )

        vals = {
            **period_vals,
            "budget_scope": "lifetime",
            "control_all_analytic_accounts": False,
            "control_analytic_account_ids": [Command.set(self.ids)],
        }
        period = (
            reference_period.sudo().copy(default=vals)
            if reference_period
            else self.env["budget.period"].sudo().create(vals)
        )
        self.sudo().write(
            {
                "budget_control_scope": "lifetime",
                "budget_period_id": period.id,
            }
        )
        return period

    def action_open_lifetime_budget_setup(self):
        """Open the atomic Lifetime Period and Budget Control setup."""
        self.ensure_one()
        active_controls = self.budget_control_ids.filtered(
            lambda control: control.active and control.state != "cancel"
        )
        if self.budget_control_scope == "lifetime":
            raise UserError(
                self.env._(
                    "Analytic %(analytic)s already uses Lifetime budgeting.",
                    analytic=self.display_name,
                )
            )
        if active_controls:
            raise UserError(
                self.env._(
                    "Archive or cancel Budget Control %(control)s before creating "
                    "a Lifetime budget for analytic %(analytic)s.",
                    control=active_controls[:1].display_name,
                    analytic=self.display_name,
                )
            )
        company = self.company_id or self.env.company
        return {
            "name": self.env._("Create Lifetime Budget"),
            "type": "ir.actions.act_window",
            "res_model": "budget.lifetime.setup",
            "view_mode": "form",
            "view_id": self.env.ref(
                "budget_control.budget_lifetime_setup_view_form"
            ).id,
            "target": "new",
            "context": {
                "default_analytic_account_id": self.id,
                "default_name": self.name,
                "default_template_id": company.budget_template_id.id,
            },
        }

    def _filter_by_analytic_account(self, val):
        return val["analytic_account_id"][0] == self.id

    @api.depends_context("budget_period_ids")
    def _compute_amount_budget_info(self):
        """Note: This method is similar to BCS._compute_budget_info"""
        BudgetPeriod = self.env["budget.period"]
        MonitorReport = self.env["budget.monitor.report"]
        query = BudgetPeriod._budget_info_query()
        analytic_ids = self.ids
        # The monitoring is a view of the budget moves
        self.env.flush_all()
        # Retrieve budgeting data for a list of budget_control
        domain = [("analytic_account_id", "in", analytic_ids)]
        # Optional filters by context
        ctx = self.env.context.copy()
        if ctx.get("budget_period_ids"):
            domain.append(("budget_period_id", "in", ctx["budget_period_ids"]))
        # --
        # The whole pool counts, whatever the user may read
        dataset_all = MonitorReport.sudo()._read_group_dataset(
            domain,
            ["analytic_account_id", "amount_type", "amount"],
            ["analytic_account_id", "amount_type"],
        )
        dataset_map = defaultdict(list)
        for data in dataset_all:
            dataset_map[data["analytic_account_id"][0]].append(data)
        forward_map = self.env["budget.balance.forward.line"]._get_forward_balance_map(
            ctx.get("budget_period_ids", []), analytic_ids
        )
        forward_totals = defaultdict(float)
        for (_period_id, analytic_id), amount in forward_map.items():
            forward_totals[analytic_id] += amount
        for rec in self:
            # Get data from dataset
            dataset = [
                data
                for data in dataset_map[rec.id]
                if rec._filter_by_analytic_account(data)
            ]
            budget_info = BudgetPeriod.get_budget_info_from_dataset(query, dataset)
            rec.amount_budget = budget_info["amount_budget"]
            rec.amount_forward_in = forward_totals[rec.id]
            rec.amount_forward_out = budget_info["amount_forward_out"]
            rec.amount_consumed = budget_info["amount_consumed"]
            rec.amount_balance = budget_info["amount_balance"]

    def _check_budget_control_status(self, budget_period_id=False):
        """Warning for budget_control on budget_period, but not in controlled"""
        domain = [("analytic_account_id", "in", self.ids)]
        if budget_period_id:
            domain.append(("budget_period_id", "=", budget_period_id))

        # Use search_read to fetch only required fields
        budget_controls = self.env["budget.control"].search_read(
            domain, ["analytic_account_id", "state"]
        )
        if not budget_controls:
            names = ", ".join(self.mapped("display_name"))
            raise UserError(
                self.env._(
                    "No budget control sheet found for the selected analytics:\n"
                    "%(names)s",
                    names=names,
                )
            )

        bc_analytics_ids = {
            bc["analytic_account_id"][0]
            for bc in budget_controls
            if bc["analytic_account_id"]
        }
        no_bc_analytics = self.filtered(lambda x: x.id not in bc_analytics_ids)

        # No budget control sheet found
        if no_bc_analytics:
            names = ", ".join(no_bc_analytics.mapped("display_name"))
            raise UserError(
                self.env._(
                    "Following analytics have no budget control sheet:\n%(names)s",
                    names=names,
                )
            )

        # Find analytics has no controlled budget control sheet
        budget_controlled_ids = {
            bc["analytic_account_id"][0]
            for bc in budget_controls
            if bc["state"] == "done"
        }
        no_cbc_analytics = self.filtered(lambda x: x.id not in budget_controlled_ids)

        if no_cbc_analytics:
            names = ", ".join(no_cbc_analytics.mapped("display_name"))
            raise UserError(
                self.env._(
                    "Budget control sheets for the following analytics "
                    "are not in control:\n%(names)s",
                    names=names,
                )
            )

    def _auto_adjust_date_commit(self, docline):
        for rec in self:
            if not rec.auto_adjust_date_commit:
                continue
            if rec.bm_date_from and rec.bm_date_from > docline.date_commit:
                docline.date_commit = rec.bm_date_from
            elif rec.bm_date_to and rec.bm_date_to < docline.date_commit:
                docline.date_commit = rec.bm_date_to
