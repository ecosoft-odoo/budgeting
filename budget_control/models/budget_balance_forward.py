# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from collections import Counter

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


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
        default=lambda self: self.env["budget.period"]._get_eligible_budget_period(),
    )
    to_budget_period_id = fields.Many2one(
        comodel_name="budget.period",
        required=True,
        ondelete="restrict",
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
    _sql_constraints = [
        ("name_uniq", "UNIQUE(name)", "Name must be unique!"),
    ]

    @api.constrains("from_budget_period_id", "to_budget_period_id")
    def _check_budget_period(self):
        for rec in self:
            if (
                rec.to_budget_period_id.bm_date_from
                <= rec.from_budget_period_id.bm_date_to
            ):
                raise ValidationError(
                    self.env._(
                        "'To Budget Period' must be later than 'From Budget Period'"
                    )
                )

    def _compute_missing_analytic(self):
        for rec in self:
            rec.missing_analytic = any(
                rec.forward_line_ids.filtered_domain(
                    [("to_analytic_account_id", "=", False)]
                )
            )

    def _get_other_forward(self):
        query = """
            SELECT fw_line.analytic_account_id
            FROM budget_balance_forward_line fw_line
            LEFT JOIN budget_balance_forward fw
                ON fw.id = fw_line.forward_id
            WHERE fw.state in ('review', 'done')
                AND fw.id != %s
                AND fw.from_budget_period_id = %s
                AND (
                    NOT EXISTS (
                        SELECT 1 FROM budget_balance_forward_company_rel r
                        WHERE r.forward_id = fw.id
                    )
                    OR EXISTS (
                        SELECT 1 FROM budget_balance_forward_company_rel r
                        WHERE r.forward_id = fw.id AND r.company_id = %s
                    )
                )
        """
        params = (self.id, self.from_budget_period_id.id, self.env.company.id)
        self.env.cr.execute(query, params)
        return self.env.cr.dictfetchall()

    def _prepare_vals_forward(self):
        """Retrieve Analytic Account relevant to from_budget_period"""
        self.ensure_one()
        # Ensure that budget info will be based on this period, and no_fwd_commit
        self = self.with_context(
            budget_period_ids=self.from_budget_period_id.ids,
            no_fwd_commit=True,
        )
        # Analyic Account from budget control sheet of the previous year
        BudgetControl = self.env["budget.control"]
        bc_domain = [("budget_period_id", "=", self.from_budget_period_id.id)]
        if self.company_ids:
            bc_domain += [("company_ids", "in", self.company_ids.ids)]
        budget_controls = BudgetControl.search(bc_domain)
        analytics = budget_controls.mapped("analytic_account_id")
        # Find document forward balance is used. it should skip it.
        query_analytic = self._get_other_forward()
        analytic_dup_ids = [x["analytic_account_id"] for x in query_analytic]
        value_dict = []
        for analytic in analytics:
            if analytic.id in analytic_dup_ids:
                continue
            method_type = False
            if (
                analytic.bm_date_to
                and analytic.bm_date_to < self.to_budget_period_id.bm_date_from
            ):
                method_type = "new"
            value_dict.append(
                {
                    "forward_id": self.id,
                    "analytic_account_id": analytic.id,
                    "method_type": method_type,
                    "amount_balance": analytic.amount_balance,
                    "amount_balance_forward": 0
                    if analytic.amount_balance < 0
                    else analytic.amount_balance,
                }
            )
        return value_dict

    def action_review_budget_balance(self):
        for rec in self:
            rec.get_budget_balance_forward()
        self.write({"state": "review"})

    def get_budget_balance_forward(self):
        """Get budget balance on each analytic account."""
        self = self.sudo()
        Line = self.env["budget.balance.forward.line"]
        for rec in self:
            vals = rec._prepare_vals_forward()
            Line.create(vals)

    def create_missing_analytic(self):
        for rec in self:
            for line in rec.forward_line_ids.filtered_domain(
                [("to_analytic_account_id", "=", False)]
            ):
                line.to_analytic_account_id = (
                    line.analytic_account_id.next_year_analytic()
                )

    def preview_budget_balance_forward_info(self):
        self.ensure_one()
        if self.missing_analytic:
            raise UserError(
                _(
                    "Some carry forward analytic accounts are missing.\n"
                    "Click 'Create Missing Analytics' button to create "
                    "for next budget period."
                )
            )
        wizard = self.env.ref("budget_control.view_budget_balance_forward_info_form")
        forward_vals = self._get_forward_initial_balance()
        return {
            "name": _("Preview Budget Balance"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "budget.balance.forward.info",
            "views": [(wizard.id, "form")],
            "view_id": wizard.id,
            "target": "new",
            "context": {
                "default_forward_id": self.id,
                "default_forward_info_line_ids": forward_vals,
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
        res = [
            {
                "analytic_account_id": analytic_id,
                "initial_available": amount,
            }
            for analytic_id, amount in res.items()
        ]
        return res

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

        PlanLine = self.env["budget.plan.line"].sudo()
        plan_lines = PlanLine.search(
            [
                ("budget_period_id", "in", target_periods.ids),
                ("analytic_account_id", "in", target_analytics.ids),
            ]
        )
        plan_lines.invalidate_recordset(["amount_forward_in", "allocated_amount"])
        plans = plan_lines.mapped("plan_id")
        plans.invalidate_recordset(["total_amount"])

        if "budget.plan.line.detail" in self.env:
            detail_plans = (
                self.env["budget.plan.line.detail"]
                .sudo()
                .search(
                    [
                        ("plan_id.budget_period_id", "in", target_periods.ids),
                        ("analytic_account_id", "in", target_analytics.ids),
                    ]
                )
                .mapped("plan_id")
            )
            detail_plans.invalidate_recordset(["total_amount"])

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
        plans = (
            self.env["budget.plan"]
            .sudo()
            .search(
                [
                    ("budget_period_id", "in", target_periods.ids),
                    ("line_ids.analytic_account_id", "in", target_analytics.ids),
                    ("state", "in", ["confirm", "done"]),
                ]
            )
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
            rec_plans = plans.filtered(
                lambda plan,
                period=rec.to_budget_period_id,
                analytics=rec_target_analytics: plan.budget_period_id == period
                and plan.line_ids.mapped("analytic_account_id") & analytics
            )
            rec_controls = controls.filtered(
                lambda control,
                period=rec.to_budget_period_id,
                analytics=rec_target_analytics: control.budget_period_id == period
                and control.analytic_account_id in analytics
            )
            submitted_controls = rec_controls.filtered(
                lambda control: control.state in ("submit", "done")
            )
            distributed_controls = rec_controls.filtered(
                lambda control: control.line_ids
                and not control.currency_id.is_zero(control.amount_budget)
            )
            used_controls = rec_controls.filtered(
                lambda control: not control.currency_id.is_zero(control.amount_consumed)
            )
            if rec_plans or submitted_controls or distributed_controls or used_controls:
                raise UserError(
                    _(
                        "You cannot cancel this Forward Balance because its target "
                        "budget has already been confirmed, submitted, controlled, "
                        "or consumed. Use the Reverse Forward process to preserve "
                        "the audit trail."
                    )
                )

    def action_budget_balance_forward(self):
        # For extend mode, make sure bm_date_to is extended
        for rec in self:
            for line in rec.forward_line_ids:
                if line.method_type == "extend":
                    line.to_analytic_account_id.bm_date_to = (
                        rec.to_budget_period_id.bm_date_to
                    )
        # --
        self.write({"state": "done"})

    def action_cancel(self):
        self.write({"state": "cancel"})

    def action_draft(self):
        self.filtered(lambda forward: forward.state == "done")._check_can_cancel()
        self.mapped("forward_line_ids").unlink()
        self.write({"state": "draft"})

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
    method_type = fields.Selection(
        selection=[
            ("new", "New"),
            ("extend", "Extend"),
        ],
        string="Method",
        help="New: if the analytic has ended, 'To Analytic Account' is required\n"
        "Extended: if the analytic has ended, "
        "but want to extend to next period date end",
    )
    to_analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Carry Forward Analytic",
        compute="_compute_to_analytic_account_id",
        store=True,
        readonly=True,
    )
    bm_date_to = fields.Date(
        related="analytic_account_id.bm_date_to",
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="forward_id.currency_id",
        readonly=True,
    )
    amount_balance_forward = fields.Monetary(
        string="Forward",
    )
    accumulate_analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Accumulate Analytic",
    )
    amount_balance_accumulate = fields.Monetary(
        string="Accumulate",
        compute="_compute_amount_balance_accumulate",
        inverse="_inverse_amount_balance_accumulate",
        store=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines.mapped("forward_id")._invalidate_forward_budget_records()
        return lines

    def write(self, vals):
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

    @api.depends("method_type")
    def _compute_to_analytic_account_id(self):
        for rec in self:
            # Case analytic has no end date, always use same analytic
            if not rec.analytic_account_id.bm_date_to:
                rec.to_analytic_account_id = rec.analytic_account_id
                rec.method_type = False
                continue
            # Case analytic has extended end date that cover new balance date,
            # use same analytic
            if (
                rec.analytic_account_id.bm_date_to
                and rec.analytic_account_id.bm_date_to
                >= rec.forward_id.to_budget_period_id.bm_date_from
            ):
                rec.to_analytic_account_id = rec.analytic_account_id
                rec.method_type = "extend"
                continue
            # Case want to extend analytic to end of next budget period
            if rec.method_type == "extend":
                rec.to_analytic_account_id = rec.analytic_account_id
                continue
            # Case want to use next analytic, if exists
            if rec.method_type == "new":
                rec.to_analytic_account_id = rec.analytic_account_id.next_year_analytic(
                    auto_create=False
                )

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
