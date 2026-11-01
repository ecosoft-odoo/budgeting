# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from collections import Counter

from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_date


class BudgetBalanceForward(models.Model):
    _name = "budget.balance.forward"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Budget Balance Forward"

    name = fields.Char(
        required=True,
    )
    from_budget_period_id = fields.Many2one(
        comodel_name="budget.period",
        required=True,
        ondelete="restrict",
        domain=[("budget_scope", "=", "fiscal")],
        default=lambda self: self.env["budget.period"]._get_eligible_budget_period(),
    )
    to_budget_period_id = fields.Many2one(
        comodel_name="budget.period",
        required=True,
        ondelete="restrict",
        domain=[("budget_scope", "=", "fiscal")],
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("review", "Review"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        readonly=True,
        copy=False,
        index=True,
        default="draft",
        tracking=True,
    )
    forward_line_ids = fields.One2many(
        comodel_name="budget.balance.forward.line",
        inverse_name="forward_id",
        string="Forward Lines",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.user.company_id.currency_id,
    )
    missing_analytic = fields.Boolean(
        compute="_compute_missing_analytic",
        help="Not all forward lines has been assigned with carry forward analytic",
    )
    company_ids = fields.Many2many(
        comodel_name="res.company",
        relation="budget_balance_forward_company_rel",
        column1="forward_id",
        column2="company_id",
        string="Companies",
        help="Restrict to specific companies. Empty = all companies.",
    )
    _name_uniq = models.Constraint(
        "UNIQUE(name)",
        "Name must be unique!",
    )

    @api.constrains("from_budget_period_id", "to_budget_period_id")
    def _check_budget_period(self):
        for rec in self:
            if (
                rec.from_budget_period_id.budget_scope != "fiscal"
                or rec.to_budget_period_id.budget_scope != "fiscal"
            ):
                raise ValidationError(
                    self.env._("Forward Budget Balance only supports Fiscal Periods.")
                )
            if (
                rec.to_budget_period_id.bm_date_from
                <= rec.from_budget_period_id.bm_date_to
            ):
                raise ValidationError(
                    self.env._(
                        "'To Budget Period' must be later than 'From Budget Period'"
                    )
                )

    @api.depends("forward_line_ids.to_analytic_account_id")
    def _compute_missing_analytic(self):
        for rec in self:
            rec.missing_analytic = any(
                rec.forward_line_ids.filtered_domain(
                    [("to_analytic_account_id", "=", False)]
                )
            )

    def _get_other_forward_lines(self, states=("review", "done")):
        """Lines of the other forwards of the source period, in ``states``,
        that may carry the balance of a company this one carries: forwards of
        all companies overlap all others."""
        self.ensure_one()
        lines = (
            self.env["budget.balance.forward.line"]
            .sudo()
            .search(
                [
                    ("forward_id", "!=", self.id),
                    ("forward_id.state", "in", list(states)),
                    (
                        "forward_id.from_budget_period_id",
                        "=",
                        self.from_budget_period_id.id,
                    ),
                ]
            )
        )
        if not self.company_ids:
            return lines
        return lines.filtered(
            lambda line: (
                not line.forward_id.company_ids
                or line.forward_id.company_ids & self.company_ids
            )
        )

    def _check_forward_duplicates(self):
        """An analytic has its balance of a period carried forward once."""
        for forward in self:
            others = forward._get_other_forward_lines(states=("done",))
            duplicates = forward.forward_line_ids.analytic_account_id & (
                others.analytic_account_id
            )
            if duplicates:
                other = others.filtered(
                    lambda line, analytic=duplicates[:1]: (
                        line.analytic_account_id == analytic
                    )
                )[:1]
                raise UserError(
                    self.env._(
                        "%(forward)s already carries the balance of %(analytic)s "
                        "from %(period)s.",
                        forward=other.forward_id.display_name,
                        analytic=duplicates[:1].display_name,
                        period=forward.from_budget_period_id.display_name,
                    )
                )

    def _prepare_vals_forward(self):
        """One line for each analytic of the active budget control sheets of
        the period, with its available balance. The commitments forwarded from
        the period no longer consume it, so the balance carries their budget
        with them."""
        self.ensure_one()
        forward = self.with_context(budget_period_ids=self.from_budget_period_id.ids)
        # Analyic Account from budget control sheet of the previous year
        BudgetControl = forward.env["budget.control"]
        bc_domain = [
            ("budget_period_id", "=", forward.from_budget_period_id.id),
            ("active", "=", True),
            ("state", "!=", "cancel"),
        ]
        if forward.company_ids:
            bc_domain += [("company_ids", "in", forward.company_ids.ids)]
        budget_controls = BudgetControl.search(bc_domain)
        analytics = budget_controls.mapped("analytic_account_id")
        # Analytics another forward of the period carries are skipped
        analytic_dup_ids = forward._get_other_forward_lines().analytic_account_id.ids
        value_dict = []
        for analytic in analytics:
            if analytic.id in analytic_dup_ids:
                continue
            value_dict.append(
                {
                    "forward_id": forward.id,
                    "analytic_account_id": analytic.id,
                    "amount_balance": analytic.amount_balance,
                    "amount_balance_forward": max(analytic.amount_balance, 0),
                }
            )
        return value_dict

    def action_review_budget_balance(self):
        for rec in self:
            rec._get_budget_balance_forward()
        self.write({"state": "review"})

    def _get_budget_balance_forward(self):
        """Get budget balance on each analytic account."""
        self.check_access("write")
        forwards = self.sudo()
        Line = forwards.env["budget.balance.forward.line"]
        for rec in forwards:
            vals = rec._prepare_vals_forward()
            Line.create(vals)

    def action_continue_analytics(self):
        """Continue the analytics of the lines without forward analytic in
        the target period."""
        self.ensure_one()
        lines = self.forward_line_ids.filtered_domain(
            [("to_analytic_account_id", "=", False)]
        )
        return self.env["budget.analytic.continue"]._get_continue_action(
            self.to_budget_period_id, lines.analytic_account_id
        )

    def _check_forward_targets(self):
        """The lines carry their balances to analytics of the target period,
        or without Budget Period open then, of the company of their analytic:
        checked before the forward completes."""
        limit = 10
        for forward in self:
            if forward.missing_analytic:
                raise UserError(
                    self.env._(
                        "Some lines have no forward analytic: click Continue "
                        "Analytics, or choose them."
                    )
                )
            messages = [
                message
                for line in forward.forward_line_ids
                if (message := line._get_target_error())
            ]
            if len(messages) > limit:
                messages[limit:] = [
                    self.env._("And %s more lines.", len(messages) - limit)
                ]
            if messages:
                raise UserError("\n".join(messages))

    def _get_open_commitment(self):
        """Commitments still in the source period on the analytics of the
        lines: forwarded first, the balance carries their budget too."""
        self.ensure_one()
        # The monitoring is a view of the budget moves
        self.env.flush_all()
        groups = (
            self.env["budget.monitor.report"]
            .sudo()
            ._read_group(
                [
                    ("budget_period_id", "=", self.from_budget_period_id.id),
                    (
                        "analytic_account_id",
                        "in",
                        self.forward_line_ids.analytic_account_id.ids,
                    ),
                    (
                        "amount_type",
                        "not in",
                        ("10_budget", "12_forward_out", "80_actual"),
                    ),
                ],
                [],
                ["amount:sum"],
            )
        )
        return -(groups[0][0] or 0.0) if groups else 0.0

    def preview_budget_balance_forward_info(self):
        self.ensure_one()
        self._check_forward_targets()
        wizard = self.env.ref("budget_control.view_budget_balance_forward_info_form")
        forward_vals = self._get_forward_initial_balance()
        return {
            "name": self.env._("Preview Budget Balance"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "budget.balance.forward.info",
            "views": [(wizard.id, "form")],
            "view_id": wizard.id,
            "target": "new",
            "context": {
                "default_forward_id": self.id,
                "default_open_commitment": self._get_open_commitment(),
                "default_forward_info_line_ids": [
                    Command.create(vals) for vals in forward_vals
                ],
            },
        }

    def _get_forward_initial_balance(self):
        """Get analytic accounts from both to_analtyic_account_id
        and accumulate_analytic_account_id"""
        self.ensure_one()

        def get_amount(k, v):
            forwards = self.env["budget.balance.forward.line"]._read_group(
                [
                    ("forward_id", "=", self.id),
                    ("forward_id.state", "in", ["review", "done"]),
                    (k, "!=", False),
                ],
                [k],
                [f"{v}:sum"],
            )
            return {analytic.id: amount for analytic, amount in forwards}

        # From to_analytic_account_id
        res_a = get_amount("to_analytic_account_id", "amount_balance_forward")
        res_b = get_amount(
            "accumulate_analytic_account_id", "amount_balance_accumulate"
        )
        # Sum amount of the same analytic, and return as list
        res = dict(Counter(res_a) + Counter(res_b))
        period = self.to_budget_period_id
        commits = self.env["budget.commit.forward.line"]._get_commit_forward_in_map(
            period.ids, list(res)
        )
        return [
            {
                "analytic_account_id": analytic_id,
                "initial_available": amount,
                "initial_commit": commits[period.id, analytic_id],
            }
            for analytic_id, amount in res.items()
        ]

    def _invalidate_forward_budget_records(self):
        """Invalidate every non-stored total affected by these documents."""
        lines = self.mapped("forward_line_ids")
        if not lines:
            return
        source_analytics = lines.mapped("analytic_account_id")
        target_analytics = lines.mapped("to_analytic_account_id") + lines.mapped(
            "accumulate_analytic_account_id"
        )
        source_periods = self.mapped("from_budget_period_id")
        target_periods = self.mapped("to_budget_period_id")

        controls = (
            self.env["budget.control"]
            .sudo()
            .search(
                [
                    ("budget_period_id", "in", (source_periods + target_periods).ids),
                    (
                        "analytic_account_id",
                        "in",
                        (source_analytics + target_analytics).ids,
                    ),
                ]
            )
        )
        controls.invalidate_recordset(
            [
                "amount_budget",
                "amount_forward_in",
                "amount_new_budget",
                "amount_forward_out",
                "amount_actual",
                "amount_commit",
                "amount_consumed",
                "amount_balance",
            ]
        )
        (source_analytics + target_analytics).invalidate_recordset(
            [
                "amount_budget",
                "amount_forward_in",
                "amount_forward_out",
                "amount_consumed",
                "amount_balance",
            ]
        )

    def _check_can_cancel(self):
        """Prevent cancelling after the target budget entered its workflow."""
        target_periods = self.mapped("to_budget_period_id")
        target_analytics = self.mapped("forward_line_ids.to_analytic_account_id")
        target_analytics += self.mapped(
            "forward_line_ids.accumulate_analytic_account_id"
        )
        controls = (
            self.env["budget.control"]
            .sudo()
            .search(
                [
                    ("budget_period_id", "in", target_periods.ids),
                    ("analytic_account_id", "in", target_analytics.ids),
                ]
            )
        )
        for rec in self:
            rec_target_analytics = rec.forward_line_ids.mapped(
                "to_analytic_account_id"
            ) + rec.forward_line_ids.mapped("accumulate_analytic_account_id")
            if not rec_target_analytics:
                continue
            target_period = rec.to_budget_period_id
            rec_controls = controls.filtered(
                lambda control, period=target_period, analytics=rec_target_analytics: (
                    control.budget_period_id == period
                    and control.analytic_account_id in analytics
                )
            )
            submitted_controls = rec_controls.filtered(
                lambda control: control.state in ("submit", "done")
            )
            distributed_controls = rec_controls.filtered(
                lambda control: (
                    control.line_ids
                    and not control.currency_id.is_zero(control.amount_budget)
                )
            )
            used_controls = rec_controls.filtered(
                lambda control: not control.currency_id.is_zero(control.amount_consumed)
            )
            if submitted_controls or distributed_controls or used_controls:
                rec._raise_target_budget_started()

    def _raise_target_budget_started(self):
        raise UserError(
            self.env._(
                "You cannot cancel this Forward Balance because its target "
                "budget has already been confirmed, submitted, controlled, "
                "or consumed. Use the Reverse Forward process to preserve "
                "the audit trail."
            )
        )

    def action_budget_balance_forward(self):
        # One by one: each forward checks the ones done before it
        for forward in self:
            forward._check_forward_targets()
            forward._check_forward_duplicates()
            forward.write({"state": "done"})

    def action_cancel(self):
        self.write({"state": "cancel"})

    def action_draft(self):
        self.filtered(lambda forward: forward.state == "done")._check_can_cancel()
        self.write({"state": "draft"})
        self.mapped("forward_line_ids").unlink()

    def write(self, vals):
        if vals.get("state") == "cancel":
            self._check_can_cancel()
        period_changed = {"from_budget_period_id", "to_budget_period_id"} & vals.keys()
        if period_changed:
            self._invalidate_forward_budget_records()
        res = super().write(vals)
        if period_changed or "state" in vals:
            self._invalidate_forward_budget_records()
        return res


class BudgetBalanceForwardLine(models.Model):
    _name = "budget.balance.forward.line"
    _description = "Budget Balance Forward Line"

    @api.model
    def _get_forward_balance_map(self, period_ids, analytic_ids):
        """Return completed forward balances keyed by period and analytic.

        Both destination fields are deliberately handled here so callers use
        the same period-aware source of truth.
        """
        result = Counter()
        if not analytic_ids:
            return result
        for analytic_field, amount_field in (
            ("to_analytic_account_id", "amount_balance_forward"),
            ("accumulate_analytic_account_id", "amount_balance_accumulate"),
        ):
            domain = [
                ("forward_id.state", "=", "done"),
                (analytic_field, "in", analytic_ids),
            ]
            if period_ids:
                domain.append(("forward_id.to_budget_period_id", "in", period_ids))
            groups = self.sudo()._read_group(
                domain,
                ["forward_id", analytic_field],
                [f"{amount_field}:sum"],
            )
            for forward, analytic, amount in groups:
                result[(forward.to_budget_period_id.id, analytic.id)] += amount
        return result

    forward_id = fields.Many2one(
        comodel_name="budget.balance.forward",
        string="Forward Balance",
        index=True,
        required=True,
        readonly=True,
        ondelete="cascade",
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        index=True,
        required=True,
        readonly=True,
    )
    amount_balance = fields.Monetary(
        string="Balance",
        required=True,
        readonly=True,
    )
    to_analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Carry Forward Analytic",
        compute="_compute_to_analytic_account_id",
        store=True,
        readonly=False,
        domain="[('control_budget', '=', True), "
        "('budget_control_scope', '=', 'fiscal')]",
        help="Analytic the balance is carried forward to: where the analytic "
        "continues in the target period by default, see Continues As.",
    )
    currency_id = fields.Many2one(
        related="forward_id.currency_id",
        readonly=True,
    )
    amount_balance_forward = fields.Monetary(
        string="Forward",
    )
    forward_changed = fields.Boolean(
        compute="_compute_forward_changed",
        help="The balance is carried elsewhere than by default: to another "
        "analytic than where its analytic continues, or partly accumulated.",
    )
    accumulate_analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Accumulate Analytic",
        domain="[('control_budget', '=', True), "
        "('budget_control_scope', '=', 'fiscal')]",
    )
    amount_balance_accumulate = fields.Monetary(
        string="Accumulate",
        compute="_compute_amount_balance_accumulate",
        inverse="_inverse_amount_balance_accumulate",
        store=True,
    )

    def _check_forward_open(self):
        """Done forwards keep what they carried, cancelled ones what they
        did."""
        if self.filtered(lambda line: line.forward_id.state in ("done", "cancel")):
            raise UserError(
                self.env._(
                    "Lines of a done or cancelled balance forward cannot change."
                )
            )

    @api.model
    def _check_forward_open_parent(self, forward_id):
        """Lines are not moved to done or cancelled forwards either."""
        forward = self.env["budget.balance.forward"].browse(forward_id)
        if forward.state in ("done", "cancel"):
            raise UserError(
                self.env._(
                    "Lines of a done or cancelled balance forward cannot change."
                )
            )

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._check_forward_open()
        lines.mapped("forward_id")._invalidate_forward_budget_records()
        return lines

    def write(self, vals):
        self._check_forward_open()
        if "forward_id" in vals:
            self._check_forward_open_parent(vals["forward_id"])
        forwards = self.mapped("forward_id")
        scope_changed = {
            "forward_id",
            "analytic_account_id",
            "to_analytic_account_id",
            "accumulate_analytic_account_id",
        } & vals.keys()
        if scope_changed:
            forwards._invalidate_forward_budget_records()
        res = super().write(vals)
        (forwards + self.mapped("forward_id"))._invalidate_forward_budget_records()
        return res

    def unlink(self):
        self._check_forward_open()
        forwards = self.mapped("forward_id")
        forwards._invalidate_forward_budget_records()
        return super().unlink()

    @api.constrains("amount_balance_forward", "amount_balance_accumulate")
    def _check_amount(self):
        for rec in self:
            if rec.amount_balance_forward < 0 or rec.amount_balance_accumulate < 0:
                raise ValidationError(self.env._("Negative amount is not allowed"))
            if rec.amount_balance_accumulate and not rec.accumulate_analytic_account_id:
                raise ValidationError(
                    self.env._(
                        "Accumulate Analytic is requried for lines when Accumulate > 0"
                    )
                )

    @api.depends(
        "analytic_account_id.next_analytic_id",
        "analytic_account_id.bm_date_from",
        "analytic_account_id.bm_date_to",
        "forward_id.to_budget_period_id",
    )
    def _compute_to_analytic_account_id(self):
        for rec in self:
            # A chosen analytic stays, and done or cancelled forwards keep
            # where they carried their lines
            if rec.to_analytic_account_id or rec.forward_id.state in (
                "done",
                "cancel",
            ):
                continue
            rec.to_analytic_account_id = rec.analytic_account_id._get_forward_analytic(
                rec.forward_id.to_budget_period_id
            )

    @api.depends("to_analytic_account_id", "amount_balance_accumulate")
    def _compute_forward_changed(self):
        for line in self:
            default = line.analytic_account_id._get_forward_analytic(
                line.forward_id.to_budget_period_id
            )
            line.forward_changed = bool(line.to_analytic_account_id) and (
                line.to_analytic_account_id != default
                or bool(line.amount_balance_accumulate)
            )

    def _get_target_error(self):
        """Why the forward cannot carry the balance of this line to its
        analytics, if it cannot."""
        self.ensure_one()
        period = self.forward_id.to_budget_period_id
        company = self.analytic_account_id.company_id
        targets = self.to_analytic_account_id
        if self.amount_balance_accumulate:
            targets |= self.accumulate_analytic_account_id
        for analytic in targets:
            if not analytic._is_forward_target(period):
                return self.env._(
                    "%(line)s: %(analytic)s cannot take budgets of %(period)s: "
                    "choose an analytic of the period, or without Budget Period, "
                    "open on %(date)s.",
                    line=self.analytic_account_id.display_name,
                    analytic=analytic.display_name,
                    period=period.display_name,
                    date=format_date(self.env, period.bm_date_from),
                )
            if (
                analytic.company_id
                and company
                and analytic.company_id not in company.parent_ids
            ):
                return self.env._(
                    "%(line)s: %(analytic)s is not of its company.",
                    line=self.analytic_account_id.display_name,
                    analytic=analytic.display_name,
                )
        return False

    @api.depends("amount_balance", "amount_balance_forward")
    def _compute_amount_balance_accumulate(self):
        for rec in self:
            if rec.amount_balance <= 0:
                rec.amount_balance_accumulate = 0
                rec.amount_balance_forward = 0
                continue
            rec.amount_balance_accumulate = (
                rec.amount_balance - rec.amount_balance_forward
            )

    @api.onchange("amount_balance_accumulate")
    def _inverse_amount_balance_accumulate(self):
        for rec in self:
            if rec.amount_balance <= 0:
                rec.amount_balance_forward = 0
                continue
            rec.amount_balance_forward = (
                rec.amount_balance - rec.amount_balance_accumulate
            )
