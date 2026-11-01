# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from collections import defaultdict
from datetime import datetime
from json import dumps

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_compare

from .analytic_plan import BUDGET_COLUMN, budget_row_key


class BaseBudgetMove(models.AbstractModel):
    _name = "base.budget.move"
    _description = "Document Budget Moves"
    _order = "analytic_account_id, date, id"

    reference = fields.Char(
        compute="_compute_reference",
        store=True,
        readonly=False,
        index=True,
        help="Reference to document number of extending model",
    )
    source_document = fields.Char(
        compute="_compute_source_document",
        store=True,
        readonly=False,
        index=True,
        help="Reference to Source document number of extending model",
    )
    template_line_id = fields.Many2one(
        comodel_name="budget.template.line",
        index=True,
    )
    kpi_id = fields.Many2one(
        comodel_name="budget.kpi",
        compute="_compute_kpi_id",
        store=True,
    )
    date = fields.Date(
        required=True,
        index=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
    )
    account_id = fields.Many2one(
        comodel_name="account.account",
        bypass_search_access=True,
        index=True,
        readonly=True,
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        bypass_search_access=True,
        index=True,
        readonly=True,
    )
    analytic_plan = fields.Many2one(
        comodel_name="account.analytic.plan",
        bypass_search_access=True,
        index=True,
        readonly=True,
    )
    amount_currency = fields.Float(
        required=True,
        digits="Budget Precision",
        help="Amount in multi currency",
    )
    credit = fields.Float(
        readonly=True,
        digits="Budget Precision",
    )
    debit = fields.Float(
        readonly=True,
        digits="Budget Precision",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.user.company_id.id,
        index=True,
    )
    note = fields.Char(
        readonly=True,
    )
    adj_commit = fields.Boolean(
        help="This budget move line is the result of "
        "Over returned 'Automatic Adjustment'",
    )
    fwd_commit = fields.Boolean(
        help="This budget move line is the result of 'Forward Budget Commitment'",
    )

    @api.depends("template_line_id")
    def _compute_kpi_id(self):
        for rec in self:
            rec.kpi_id = rec.template_line_id.kpi_id

    def _compute_reference(self):
        """Compute reference name of the budget move document"""
        self.update({"reference": False})

    def _compute_source_document(self):
        """Compute source document of the budget move document"""
        self.update({"source_document": False})

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        self.env["account.analytic.plan"]._patch_budget_plan_view(
            arch, view_type, self._name
        )
        return arch, view

    @api.model
    def _get_plan_column_vals(self, analytics):
        """``{x_plan<id>_id: account id}`` for the given analytic accounts that
        have a column (see ``account.analytic.plan._sync_budget_columns``)."""
        return self.env["account.analytic.plan"]._get_budget_column_vals(
            analytics, self._name
        )

    def _get_budget_row_key(self):
        """Key of the analytic distribution row this move commits."""
        self.ensure_one()
        return self.env["account.analytic.plan"]._get_budget_row_key(self)


class BudgetDoclineMixinBase(models.AbstractModel):
    _name = "budget.docline.mixin.base"
    _description = (
        "Base of budget.docline.mixin, used for non budgeting model extension"
    )
    _budget_analytic_field = "analytic_distribution"
    # Budget related variables
    _budget_date_commit_fields = []  # Date used for budget commitment
    _budget_move_model = False  # account.budget.move
    _budget_move_field = "budget_move_ids"
    _doc_rel = False  # Reference to header object of docline
    _no_date_commit_states = [
        "draft",
        "cancel",
        "rejected",
    ]  # Never set date commit states

    @api.model
    def _get_budget_analytic_rows(self, distribution):
        """Return ``[(budget_analytic_ids, account_ids, percent)]``, one item
        per row (key) of an analytic distribution. Budget analytics are the
        accounts of root plans with Control Budget ticked. Deleted accounts
        are left out, and rows left with the same accounts are merged."""
        if not distribution:
            return []
        rows = [
            ({int(aid) for aid in str(key).split(",")}, percent)
            for key, percent in distribution.items()
        ]
        Analytic = self.env["account.analytic.account"]
        analytic_ids = tuple(sorted(set().union(*(ids for ids, _p in rows))))
        control_budget = Analytic._get_analytic_control_budget(analytic_ids)
        percents = defaultdict(float)
        for ids, percent in rows:
            percents[frozenset(aid for aid in ids if aid in control_budget)] += percent
        return [
            ({aid for aid in ids if control_budget[aid]}, set(ids), percent)
            for ids, percent in percents.items()
        ]

    @api.model
    def _get_budget_analytic_percents(self, distribution):
        """Return ``{analytic_id: percent}`` for the budget analytics of an
        analytic distribution: each row gives its full percentage to its
        budget analytic, as Odoo does for analytic lines."""
        percents = defaultdict(float)
        for analytic_ids, _ids, percent in self._get_budget_analytic_rows(distribution):
            for analytic_id in analytic_ids:
                percents[analytic_id] += percent
        return dict(percents)

    def _get_budget_analytic_percent(self, analytic_id):
        """Percentage of the line that ``analytic_id`` commits: the row being
        committed (see ``_prepare_commit_vals()``), else all its rows."""
        if "budget_row_percent" in self.env.context:
            return self.env.context["budget_row_percent"]
        return self._get_budget_analytic_percents(
            self[self._budget_analytic_field]
        ).get(analytic_id, 0.0)

    @api.model
    def _check_budget_analytic_distribution(self, distribution, partial=False):
        """A row charges at most one budget analytic, holds one account per
        plan, and the rows that charge a budget cover 100% of the line, unless
        ``partial`` (some rows of a line only)."""
        rows = self._get_budget_analytic_rows(distribution)
        Analytic = self.env["account.analytic.account"]
        for analytic_ids, ids, _percent in rows:
            if len(analytic_ids) > 1:
                names = Analytic.browse(analytic_ids).mapped("display_name")
                raise UserError(
                    self.env._(
                        "Only one budget-controlled analytic account is allowed "
                        "per analytic row:\n%s\nPlease split them into separate rows.",
                        "\n".join(f"- {name}" for name in names),
                    )
                )
            # Each plan has one column on budget moves
            accounts = Analytic.sudo().browse(ids)
            if analytic_ids and len(accounts.root_plan_id) < len(accounts):
                raise UserError(
                    self.env._(
                        "Only one account of each plan is allowed per analytic "
                        "row:\n%s\nPlease split them into separate rows.",
                        "\n".join(
                            f"- {name}" for name in accounts.mapped("display_name")
                        ),
                    )
                )
        if partial:
            return
        budget_percents = [
            percent for analytic_ids, _ids, percent in rows if analytic_ids
        ]
        precision = self.env["decimal.precision"].precision_get("Percentage Analytic")
        if (
            budget_percents
            and float_compare(sum(budget_percents), 100.0, precision_digits=precision)
            != 0
        ):
            raise UserError(
                self.env._(
                    "The total sum percent of Analytic Account must 100%. "
                    "Please check again."
                )
            )

    def _convert_analytics(self, analytic_distribution=False):
        """Return the budget analytics of the docline, or of the given
        distribution."""
        Analytic = self.env["account.analytic.account"]
        analytics = analytic_distribution or self[self._budget_analytic_field]
        if not analytics:
            return Analytic
        if self._budget_analytic_field == "analytic_distribution":
            analytics = Analytic.browse(
                list(self._get_budget_analytic_percents(analytics))
            )
        return analytics


class BudgetDoclineMixin(models.AbstractModel):
    _name = "budget.docline.mixin"
    _inherit = ["budget.docline.mixin.base"]
    _description = "Mixin used in each document line model that commit budget"

    can_commit = fields.Boolean(
        compute="_compute_can_commit",
        help="If True, this docline is eligible to create budget move",
    )
    amount_commit = fields.Json(
        compute="_compute_commit",
        copy=False,
        store=True,
    )
    date_commit = fields.Date(
        compute="_compute_commit",
        store=True,
        copy=False,
        readonly=False,  # Allow manual entry of this field
    )
    auto_adjust_date_commit = fields.Boolean(
        compute="_compute_auto_adjust_date_commit",
        readonly=True,
    )
    fwd_analytic_distribution = fields.Json(
        string="Carry Forward Analytic",
        copy=False,
        help="If specified, recompute budget will take this into account",
    )
    fwd_date_commit = fields.Date(
        string="Carry Forward Date Commit",
        copy=False,
        readonly=False,
        help="If specified, recompute budget will take this into account",
    )
    json_budget_popover = fields.Char(
        compute="_compute_json_budget_popover",
        help="Show budget condition of selected Analytic",
    )

    def _budget_model(self):
        model = self.env.context.get("alt_budget_move_model")
        if model in self.env["account.analytic.plan"]._get_budget_move_models():
            return model
        return self._budget_move_model

    def _budget_field(self):
        # Budget moves are written with sudo(): only accept a budget move field
        fname = self.env.context.get("alt_budget_move_field")
        field = fname and self._fields.get(fname)
        if (
            field
            and field.type == "one2many"
            and field.comodel_name == self._budget_model()
        ):
            return fname
        return self._budget_move_field

    def _call_budget_method_guarded(self, method_name):
        """Call <method_name>() unless it's already in progress for this
        exact recordset higher up the current call stack (write() MRO can
        re-enter for the same records).
        """
        if not self:
            return
        in_progress = getattr(self.env.cr, "_budget_recompute_in_progress", None)
        if in_progress is None:
            in_progress = set()
            self.env.cr._budget_recompute_in_progress = in_progress
        key = (self._name, method_name, frozenset(self.ids))
        if key in in_progress:
            return
        in_progress.add(key)
        try:
            getattr(self, method_name)()
        finally:
            in_progress.discard(key)

    def _valid_commit_state(self):
        raise ValidationError(self.env._("No implementation error!"))

    @api.depends(lambda self: [self._budget_analytic_field])
    def _compute_auto_adjust_date_commit(self):
        """Auto adjust is True if some analytic account is checked auto adjust"""
        for docline in self:
            analytics = docline._convert_analytics()
            docline.auto_adjust_date_commit = any(
                aa.auto_adjust_date_commit for aa in analytics
            )

    @api.depends()
    def _compute_can_commit(self):
        """Determine if this document is eligible for budget commitment."""
        # All required fields are set
        required_fields = self._required_fields_to_commit()
        domain = [(field, "!=", False) for field in required_fields]
        records = self.filtered_domain(domain)
        records.update({"can_commit": True})
        (self - records).update({"can_commit": False})

    def _filter_current_move(self, analytic):
        self.ensure_one()
        return self.budget_move_ids.filtered(
            lambda move, analytic=analytic: move.analytic_account_id == analytic
        )

    @api.depends("budget_move_ids", "budget_move_ids.date")
    def _compute_commit(self):
        """
        - Calc amount_commit from all budget_move_ids, by analytic
          distribution row (see ``budget_row_key()``)
        - Calc date_commit if not exists and on 1st budget_move_ids only or False
        """
        analytic_field = self._budget_analytic_field
        for rec in self:
            # The rows of the line and of its carried forward commitment, then
            # those of its budget moves
            amount_commit_json = {}
            for distribution in (rec[analytic_field], rec.fwd_analytic_distribution):
                for analytic_ids, ids, _percent in rec._get_budget_analytic_rows(
                    distribution
                ):
                    if analytic_ids:
                        amount_commit_json[budget_row_key(ids)] = 0.0
            for move in rec.budget_move_ids:
                key = move._get_budget_row_key()
                amount_commit_json[key] = (
                    amount_commit_json.get(key, 0.0) + move.debit - move.credit
                )
            if not amount_commit_json:
                continue
            rec.amount_commit = amount_commit_json

            # Compute date commit
            if rec.budget_move_ids:
                rec.date_commit = min(rec.budget_move_ids.mapped("date"))

    def _compute_json_budget_popover(self):
        FloatConverter = self.env["ir.qweb.field.float"]
        periods = {}  # (analytic id, date commit, company id): budget period
        for rec in self:
            analytic_distribution = rec[self._budget_analytic_field]
            analytic_account = rec._convert_analytics(
                analytic_distribution=analytic_distribution
            )
            if not analytic_account:
                rec.json_budget_popover = False
                continue
            analytic_values = []
            company = rec[rec._doc_rel].company_id
            for analytic in analytic_account:
                key = (analytic.id, rec.date_commit, company.id)
                if key not in periods:
                    periods[key] = (
                        self.env["budget.period"]
                        .with_company(company)
                        .with_context(budget_analytic_id=analytic.id)
                        ._get_eligible_budget_period(date=rec.date_commit)
                    )
                budget_period = periods[key]
                scoped_analytic = analytic.with_context(
                    budget_period_ids=budget_period.ids
                )
                analytic_values.append(
                    {
                        "id": analytic.id,
                        "name": analytic.display_name,
                        "budget": FloatConverter.value_to_html(
                            scoped_analytic.amount_budget,
                            {"decimal_precision": "Budget Precision"},
                        ),
                        "consumed": FloatConverter.value_to_html(
                            scoped_analytic.amount_consumed,
                            {"decimal_precision": "Budget Precision"},
                        ),
                        "balance": FloatConverter.value_to_html(
                            scoped_analytic.amount_balance,
                            {"decimal_precision": "Budget Precision"},
                        ),
                    }
                )
            rec.json_budget_popover = dumps(
                {
                    "title": self.env._("Budget Figure"),
                    "analytic": analytic_values,
                }
            )

    def _get_budget_date_commit(self, docline):
        dates = [
            docline.mapped(f)[0]
            for f in self._budget_date_commit_fields
            if docline.mapped(f)[0]
        ]
        if dates:
            if isinstance(dates[0], datetime):
                date_commit = fields.Datetime.context_timestamp(self, dates[0])
            else:
                date_commit = dates[0]
        else:
            date_commit = False
        return date_commit

    def _set_date_commit(self):
        """Default implementation, use date from _doc_date_field
        which is mostly write_date during budget commitment"""
        self.ensure_one()
        # skip_account_move_synchronization = True, as this can be account.move.line
        # skipping to avoid warning error when update date_commit
        docline = self.with_context(skip_account_move_synchronization=True)
        # Use the force_date_commit if it's set in the context.
        if self.env.context.get("force_date_commit"):
            docline.date_commit = self.env.context["force_date_commit"]
            return
        if not self._budget_date_commit_fields:
            raise ValidationError(
                self.env._("'_budget_date_commit_fields' is not set!")
            )
        analytic = docline._convert_analytics()
        # If the analytic field is not set, set the date commit to False and return.
        if not analytic:
            docline.date_commit = False
            return
        # If the date commit is already set, return.
        if docline.date_commit:
            return
        # Get dates following _budget_date_commit_fields
        docline.date_commit = self._get_budget_date_commit(docline)
        # If the date_commit is not in the analytic date range, use a possible date.
        analytic._auto_adjust_date_commit(docline)

    def _get_amount_convert_currency(
        self, amount_currency, currency, company, date_commit
    ):
        return currency._convert(
            amount_currency, company.currency_id, company, date_commit
        )

    def _get_analytic_budget_control(self, analytic, date_commit, company):
        """Return the controlled budget control of analytic at date_commit, for
        a document of company. Batches pass a ``_budget_control_cache`` dict in
        context to look each one up once."""
        cache = self.env.context.get("_budget_control_cache")
        key = (analytic.id, date_commit, company.id)
        if cache is not None and key in cache:
            return cache[key]
        period = (
            self.env["budget.period"]
            .with_company(company)
            .with_context(budget_analytic_id=analytic.id)
            ._get_eligible_budget_period(date=date_commit)
        )
        budget_control = self.env["budget.control"]
        if period:
            budget_control = budget_control.sudo().search(
                [
                    ("analytic_account_id", "=", analytic.id),
                    ("budget_period_id", "=", period.id),
                    ("state", "=", "done"),
                ],
                limit=1,
            )
        if cache is not None:
            cache[key] = budget_control
        return budget_control

    def _update_budget_commitment(self, budget_vals, analytic, reverse=False):
        self.ensure_one()
        # Document company
        document_company = self[self._doc_rel].company_id
        account = self.account_id
        budget_moves = self[self._budget_field()]
        date_commit = budget_vals.get(
            "date",
            max(budget_moves.mapped("date")) if budget_moves else self.date_commit,
        )
        currency = hasattr(self, "currency_id") and self.currency_id or False
        amount = budget_vals["amount_currency"]  # init
        today = fields.Date.context_today(self)
        budget_control = self._get_analytic_budget_control(
            analytic, date_commit or today, document_company
        )
        # A company uses the budget of its own (or its parents') analytic
        # accounts, within the allowed companies of the controlled sheet.
        # Returning an existing commitment is always possible.
        returning = reverse and budget_moves.filtered(
            lambda move: move.analytic_account_id == analytic
        )
        # The other accounts of the row, e.g. its fund, too
        row_accounts = analytic | analytic.browse(
            [
                account_id
                for fname, account_id in budget_vals.items()
                if BUDGET_COLUMN.fullmatch(fname) and account_id
            ]
        )
        denied = row_accounts.sudo().filtered(
            lambda account: (
                account.company_id
                and account.company_id not in document_company.parent_ids
            )
        )
        if (
            not denied
            and budget_control
            and not budget_control._is_company_allowed(document_company)
        ):
            denied = analytic
        if not returning and denied:
            raise UserError(
                self.env._(
                    "Company %(company)s is not allowed to use the budget of "
                    "%(analytic)s.",
                    company=document_company.name,
                    analytic=denied[:1].display_name,
                )
            )
        # Block cross-currency commits: document company currency must match
        # the budget control currency to prevent incorrect budget consumption.
        bc_currency = budget_control.currency_id
        if bc_currency and bc_currency != document_company.currency_id:
            raise UserError(
                self.env._(
                    "Company %(company)s (%(company_currency)s) cannot commit to a "
                    "%(budget_currency)s budget. "
                    "All companies sharing a budget must use the same currency.",
                    company=document_company.name,
                    company_currency=document_company.currency_id.name,
                    budget_currency=bc_currency.name,
                )
            )
        if (
            not self.env.context.get("use_amount_commit")
            and currency
            and currency != document_company.currency_id
        ):
            amount = self._get_amount_convert_currency(
                budget_vals["amount_currency"],
                currency,
                document_company,
                date_commit or today,
            )
        # NOTE: This is to handle the case of budget revenue.
        if (
            self._name == "account.move.line"
            and self.move_id.move_type == "out_invoice"
        ):
            reverse = True
        # By default, commit date is equal to document date
        # this is correct for normal case, but may require different date
        # in case of budget that carried to new period/year
        res = {
            "product_id": self.product_id.id,
            "account_id": account.id,
            "analytic_account_id": analytic.id,
            "analytic_plan": analytic.plan_id.id,
            "date": date_commit or today,
            "amount_currency": budget_vals["amount_currency"],
            "debit": not reverse and amount or 0,
            "credit": reverse and amount or 0,
            "company_id": document_company.id,
        }
        if sum([res["debit"], res["credit"]]) < 0:
            res["debit"], res["credit"] = abs(res["credit"]), abs(res["debit"])
        budget_vals.update(res)
        return budget_vals

    def _update_template_line(self, budget_move):
        """Set the KPI of ``budget_move``, one move of this docline."""
        self.ensure_one()
        BudgetPeriod = (
            self.env["budget.period"]
            .with_company(self[self._doc_rel].company_id)
            .with_context(budget_analytic_id=budget_move.analytic_account_id.id)
        )
        budget_period = BudgetPeriod._get_eligible_budget_period(self.date_commit)
        if not budget_period:
            return budget_move
        controls = BudgetPeriod.with_context(need_control=True)._prepare_controls(
            budget_period, self
        )
        template_lines = budget_period.template_id.line_ids
        # Get KPI, when possible.
        if controls and template_lines:
            template_line = BudgetPeriod._get_kpi_by_control_key(
                template_lines, controls[0], budget_period=budget_period
            )
            if not template_line:
                return budget_move
            budget_move.template_line_id = template_line.id
            # Set KPI for check budget
            budget_move.kpi_id = template_line.kpi_id.id
        return budget_move

    @api.model
    def _update_template_line_batch(self, budget_moves, period_dates=None):
        """Assign template/KPI once per period and budget control key.

        The single-record path resolves the same budget period and template line
        for every document line.  In a large invoice that means repeating the
        same searches hundreds of times.  Grouping the newly-created moves keeps
        the result identical while reducing the database work to one resolution
        and one write per distinct group.

        ``period_dates`` allows callers to preserve the single-record behavior
        when the period lookup date differs from the budget move date.
        """
        if not budget_moves:
            return budget_moves

        period_dates = period_dates or {}
        BudgetPeriod = self.env["budget.period"]
        periods_by_analytic_date = {}
        grouped_move_ids = {}
        group_periods = {}

        for move in budget_moves:
            # The budget settings of the company of the document
            control_key = move.company_id.budget_control_key
            if move.account_id.budget_bypass or not move[control_key]:
                continue
            period_date = period_dates.get(move.id, move.date)
            period_key = (move.analytic_account_id.id, period_date, move.company_id.id)
            if period_key not in periods_by_analytic_date:
                periods_by_analytic_date[period_key] = (
                    BudgetPeriod.with_company(move.company_id)
                    .with_context(budget_analytic_id=move.analytic_account_id.id)
                    ._get_eligible_budget_period(period_date)
                )
            period = periods_by_analytic_date[period_key]
            if not period:
                continue
            key = (
                period.id,
                move.analytic_account_id.id,
                move.company_id.id,
                control_key,
                move[control_key].id,
            )
            grouped_move_ids.setdefault(key, []).append(move.id)
            group_periods[key] = period

        for key, move_ids in grouped_move_ids.items():
            period = group_periods[key]
            template_lines = period.template_id.line_ids
            if not template_lines:
                continue
            _period_id, _analytic_id, company_id, control_key, control_id = key
            template_line = BudgetPeriod.with_company(
                company_id
            )._get_kpi_by_control_key(
                template_lines,
                {control_key: control_id},
                budget_period=period,
            )
            if template_line:
                budget_moves.browse(move_ids).write(
                    {
                        "template_line_id": template_line.id,
                        "kpi_id": template_line.kpi_id.id,
                    }
                )
        return budget_moves

    def _get_domain_fwd_line(self, docline):
        return [
            ("res_model", "=", docline._name),
            ("res_id", "=", docline.id),
            ("forward_id.state", "=", "done"),
        ]

    def _get_budget_forward_lines(self, date=None):
        """Lines of the done commitment forwards of this docline, those to
        ``date`` or before if given."""
        self.ensure_one()
        lines = (
            self.env["budget.commit.forward.line"]
            .sudo()
            .search(self._get_domain_fwd_line(self))
        )
        if date:
            lines = lines.filtered(lambda line: line.forward_id.to_date_commit <= date)
        return lines

    def _get_budget_forward_date(self):
        """Date the commitment of this docline is carried forward to, if any."""
        dates = self._get_budget_forward_lines().mapped("forward_id.to_date_commit")
        return max(dates, default=False)

    def _get_budget_row_dates(self):
        """Commitment date of the forwarded rows of this docline: the date of
        the last done forward that carried each row. The other rows keep the
        commitment date of the docline."""
        self.ensure_one()
        dates = {}
        lines = self._get_budget_forward_lines()
        for forward_date in sorted(set(lines.mapped("forward_id.to_date_commit"))):
            forwarded = lines.filtered(
                lambda line, forward_date=forward_date: (
                    line.forward_id.to_date_commit == forward_date
                )
            )
            # A forward may carry a row to the row another one leaves
            for line in forwarded:
                dates.pop(line._get_budget_row_key(), None)
            for line in forwarded:
                dates[line._get_target_row_key()] = forward_date
        return dates

    def _get_budget_rows_at(self, date):
        """Row keys of the commitment of this docline at ``date``: those of its
        analytic distribution, each moved to its target row by the done
        forwards to that date, in their order."""
        self.ensure_one()
        rows = {
            budget_row_key(int(aid) for aid in str(key).split(","))
            for key in self[self._budget_analytic_field] or {}
        }
        lines = self._get_budget_forward_lines(date)
        for forward_date in sorted(set(lines.mapped("forward_id.to_date_commit"))):
            forwarded = lines.filtered(
                lambda line, forward_date=forward_date: (
                    line.forward_id.to_date_commit == forward_date
                )
            )
            rows -= {line._get_budget_row_key() for line in forwarded}
            rows |= {line._get_target_row_key() for line in forwarded}
        return rows

    def _check_budget_forward_row(self, row_key):
        """Whether a forward can carry this docline to the row ``row_key``:
        the row passes the check of the analytic distribution of the
        docline, e.g. its mandatory plans, if the docline has one."""
        self.ensure_one()
        if not hasattr(self, "_validate_analytic_distribution"):
            return True
        docline = self.new({self._budget_analytic_field: {row_key: 100}}, origin=self)
        try:
            docline.with_context(
                validate_analytic=True
            )._validate_analytic_distribution()
        except ValidationError:
            return False
        return True

    def forward_commit(self):
        # allow all user can do it because this is common function
        doclines = self.sudo()
        ForwardLine = doclines.env["budget.commit.forward.line"]
        BudgetPeriod = doclines.env["budget.period"]
        for docline in doclines:
            if not docline.fwd_analytic_distribution or not docline.fwd_date_commit:
                continue
            if (
                docline[doclines._budget_analytic_field]
                == docline.fwd_analytic_distribution
                and docline.date_commit == docline.fwd_date_commit
            ):  # no forward to same date
                continue
            # Forwards are done before their documents are recomputed, and
            # a document can be forwarded more than once.
            fwd_lines = ForwardLine.search(doclines._get_domain_fwd_line(docline))
            for fwd_line in fwd_lines:
                # find last date of carry forward
                budget_period = BudgetPeriod.with_company(
                    docline[docline._doc_rel].company_id
                )._get_eligible_budget_period(fwd_line.date_commit)
                # create commitment carry (credit)
                budget_move = docline.with_context(
                    use_amount_commit=True,
                    commit_note=doclines.env._("Commitment carry forward"),
                    fwd_commit=True,
                    fwd_amount_commit=fwd_line.amount_commit,
                ).commit_budget(
                    reverse=True,
                    date=budget_period.bm_date_to,
                    analytic_distribution={
                        fwd_line._get_budget_row_key(): fwd_line.analytic_percent * 100
                    },
                )
                # create commitment carry (debit)
                if budget_move:
                    fwd_budget_move = budget_move.copy()
                    debit = fwd_budget_move.debit
                    credit = fwd_budget_move.credit
                    fwd_budget_move.write(
                        {
                            "analytic_account_id": fwd_line.to_analytic_account_id.id,
                            "date": fwd_line.forward_id.to_date_commit,
                            "credit": debit,
                            "debit": credit,
                            **fwd_line._get_target_column_vals(fwd_budget_move._name),
                        }
                    )

    def _check_required_analytic(self):
        """
        Require a budget analytic on all documents except
            - context skip required analytic
            - move that check 'Not Affect Budget'
            - line that check 'Not Affect Budget' (account.move.line only)
            - move that have 'Tax'
            - payment entry (auto-generated from account.payment)
            - bank statement entry (auto-generated from bank statement)
            - section/note line (display_type set), i.e. not a real product line
        """
        required_analytic = self.env.user.has_group(
            "budget_control.group_required_analytic"
        )
        if self.env.context.get("skip_required_analytic"):
            return False

        # A real budget line requires an analytic account; section/note lines don't.
        # - account.move.line flags real lines with display_type == "product"
        # - other doclines (purchase, sale, ...) use a falsy display_type for real
        #   lines, and some (hr.expense, purchase.request.line) have no display_type
        #   field at all -> the line is always a real product line.
        if self._name == "account.move.line":
            is_product_line = self.display_type == "product"
        else:
            is_product_line = not getattr(self, "display_type", False)
        return (
            required_analytic
            and not self._convert_analytics()
            and not (
                self._name == "account.move.line"
                and (
                    self.move_id.not_affect_budget
                    or self.not_affect_budget
                    or self.tax_line_id
                    or self.move_id.origin_payment_id
                    or self.move_id.statement_line_id
                )
            )
            and is_product_line
        )

    def commit_budget(self, reverse=False, **vals):
        """Create budget commit for each docline"""
        if not reverse:
            # Budget moves are written with sudo(): commit own documents only
            self.check_access("write")
        if self._check_required_analytic():
            raise UserError(self.env._("Please fill analytic account."))
        self.prepare_commit()
        to_commit = self.env.context.get("force_commit") or self._valid_commit_state()
        if self.can_commit and to_commit:
            budget_commit_vals = self._prepare_commit_vals(reverse=reverse, **vals)
            if not budget_commit_vals:
                return False
            budget_moves = (
                self.env[self._budget_model()].sudo().create(budget_commit_vals)
            )
            # Update Template Line, of each move: one per analytic row
            budget_move = budget_moves.browse().union(
                self._update_template_line(move) for move in budget_moves
            )
            if reverse:  # On reverse, make sure not over returned
                self.env["budget.period"].check_over_returned_budget(self)
            return budget_move
        else:
            self[self._budget_field()].sudo().unlink()

    def _get_budget_commit_rows(self, vals):
        """Return ``[(analytic_id, account_ids, percent)]``, the rows of the
        analytic distribution that charge a budget analytic: those of the line,
        or of ``analytic_distribution`` in ``vals`` (some rows only, e.g. a
        carried forward commitment). ``analytic_account_id`` in ``vals`` keeps
        the rows of that budget analytic, else its committed rows."""
        distribution = vals.pop("analytic_distribution", False)
        analytic = vals.pop("analytic_account_id", False)
        if self._budget_analytic_field != "analytic_distribution":
            rows = [
                (rec.id, {rec.id}, 100.0)
                for rec in self._convert_analytics(analytic_distribution=distribution)
            ]
        else:
            # Rows given for a line, or of one analytic, may not cover it all
            partial = bool(distribution or analytic)
            distribution = distribution or self[self._budget_analytic_field]
            self._check_budget_analytic_distribution(distribution, partial=partial)
            rows = [
                (next(iter(analytic_ids)), ids, percent)
                for analytic_ids, ids, percent in self._get_budget_analytic_rows(
                    distribution
                )
                if analytic_ids
            ]
        if not analytic:
            return rows
        analytic_rows = [row for row in rows if row[0] == analytic.id]
        if analytic_rows:
            return analytic_rows
        keys = {
            move._get_budget_row_key()
            for move in self[self._budget_field()]
            if move.analytic_account_id == analytic
        } or {str(analytic.id)}
        return [
            (analytic.id, {int(aid) for aid in key.split(",")}, 0.0)
            for key in sorted(keys)
        ]

    def _prepare_commit_vals(self, reverse=False, **vals):
        """Return budget-move values without creating records, one for each
        row of the analytic distribution that charges a budget analytic."""
        self.ensure_one()
        rows = self._get_budget_commit_rows(vals)
        ctx = self.env.context
        return_amount = ctx.get("return_amount_commit") if reverse else None
        if len(rows) > 1 and (
            ctx.get("fwd_amount_commit")
            or (
                reverse
                and "return_amount_commit" in ctx
                and not isinstance(return_amount, dict)
            )
        ):
            raise UserError(
                self.env._(
                    "%s has several analytic rows: give the amount of each row.",
                    self.display_name,
                )
            )
        Analytic = self.env["account.analytic.account"]
        BudgetMove = self.env[self._budget_model()]
        budget_commit_vals = []
        for analytic_id, account_ids, percent in rows:
            analytic = Analytic.browse(analytic_id)
            row_key = budget_row_key(account_ids)
            docline = self.with_context(budget_row_percent=percent)
            budget_vals = docline._init_docline_budget_vals(dict(vals), analytic_id)
            budget_vals = docline._budget_include_tax(budget_vals)
            if ctx.get("use_amount_commit"):
                budget_vals["amount_currency"] = (self.amount_commit or {}).get(
                    row_key, 0.0
                )
            if ctx.get("fwd_amount_commit"):
                budget_vals["amount_currency"] = ctx["fwd_amount_commit"]
            if reverse and "return_amount_commit" in ctx:
                budget_vals["amount_currency"] = (
                    return_amount.get(row_key, 0.0)
                    if isinstance(return_amount, dict)
                    else return_amount
                )
            # Record every analytic account of the row, one column per plan
            budget_vals.update(
                BudgetMove._get_plan_column_vals(Analytic.browse(account_ids))
            )
            budget_vals = self._update_budget_commitment(
                budget_vals, analytic, reverse=reverse
            )
            budget_vals.update(
                {
                    "note": ctx.get("commit_note"),
                    "adj_commit": ctx.get("adj_commit"),
                    "fwd_commit": ctx.get("fwd_commit"),
                }
            )
            if not budget_vals["amount_currency"]:
                continue
            budget_commit_vals.append(budget_vals)
        return budget_commit_vals

    def prepare_commit_batch(self, preserved_dates=None):
        """Set commitment dates in grouped writes, then validate each line."""
        preserved_dates = preserved_dates or {}
        force_date = self.env.context.get("force_date_commit")
        if force_date:
            force_date = fields.Date.to_date(force_date)
        eligible = self.filtered(
            lambda line: (
                line[line._doc_rel].state not in line._no_date_commit_states
                or self.env.context.get("force_commit")
            )
        )
        groups = {}
        for docline in eligible:
            analytics = docline._convert_analytics()
            if not analytics:
                target_date = False
            elif not force_date and (
                preserved_dates.get(docline.id) or docline.date_commit
            ):
                target_date = preserved_dates.get(docline.id) or docline.date_commit
            else:
                if force_date:
                    target_date = force_date
                else:
                    if not docline._budget_date_commit_fields:
                        raise ValidationError(
                            self.env._("'_budget_date_commit_fields' is not set!")
                        )
                    target_date = docline._get_budget_date_commit(docline)
                    if target_date:
                        # Datetime sources such as write_date are converted to the
                        # user's timezone by _get_budget_date_commit().  Normalize
                        # them to a date before comparing with the analytic period.
                        target_date = fields.Date.to_date(target_date)
                for analytic in analytics.filtered("auto_adjust_date_commit"):
                    if analytic.bm_date_from and analytic.bm_date_from > target_date:
                        target_date = analytic.bm_date_from
                    elif analytic.bm_date_to and analytic.bm_date_to < target_date:
                        target_date = analytic.bm_date_to
            if docline.date_commit != target_date:
                groups.setdefault(target_date, self.env[self._name])
                groups[target_date] |= docline

        for target_date, doclines in groups.items():
            doclines.with_context(skip_account_move_synchronization=True).write(
                {"date_commit": target_date}
            )
        for docline in eligible.filtered("can_commit"):
            docline._check_date_commit()
        return eligible

    def recompute_budget_move_batch(self):
        """Recreate commitments for a recordset with batched unlink/create/write."""
        doclines = self
        # date_commit is computed from budget moves on several document types.
        # Capture it before unlinking, just as the former per-line recompute did,
        # otherwise unlink can clear the date and make a later recompute use the
        # document's new write_date (notably after an advance return/payment).
        preserved_dates = {docline.id: docline.date_commit for docline in doclines}
        doclines.mapped(doclines._budget_field()).sudo().unlink()
        for docline in doclines:
            if docline._check_required_analytic():
                raise UserError(self.env._("Please fill analytic account."))
        doclines.prepare_commit_batch(preserved_dates=preserved_dates)

        to_commit = doclines.filtered(
            lambda line: (
                line.can_commit
                and (self.env.context.get("force_commit") or line._valid_commit_state())
            )
        )
        budget_vals = []
        # Look up each budget control once for the whole batch
        for docline in to_commit.with_context(_budget_control_cache={}):
            budget_vals.extend(docline._prepare_commit_vals())
        if not budget_vals:
            return self.env[doclines._budget_model()]
        budget_moves = self.env[doclines._budget_model()].sudo().create(budget_vals)
        return doclines._update_template_line_batch(budget_moves)

    def _can_batch_budget_precommit(self):
        """Opt in only when batch precommit matches commit_budget() semantics."""
        return False

    def _create_precommit_budget_moves_batch(self):
        """Create temporary forced commitments and preserve per-line dates."""
        doclines = self.sudo()
        reset_date_lines = doclines.filtered(lambda line: not line.date_commit)
        force_doclines = doclines.with_context(force_commit=True)

        for line in force_doclines:
            if line._check_required_analytic():
                raise UserError(self.env._("Please fill analytic account."))

        force_doclines.prepare_commit_batch()
        to_commit = force_doclines.filtered("can_commit")
        not_to_commit = force_doclines - to_commit
        if not_to_commit:
            not_to_commit.mapped(not_to_commit._budget_field()).unlink()

        budget_vals = []
        move_period_dates = []
        # Look up each budget control once for the whole batch
        for line in to_commit.with_context(_budget_control_cache={}):
            line_vals = line._prepare_commit_vals()
            budget_vals.extend(line_vals)
            move_period_dates.extend([line.date_commit] * len(line_vals))
        if not budget_vals:
            return force_doclines.env[force_doclines._budget_model()], reset_date_lines

        budget_moves = force_doclines.env[force_doclines._budget_model()].create(
            budget_vals
        )
        period_dates = dict(zip(budget_moves.ids, move_period_dates, strict=False))
        to_commit._update_template_line_batch(budget_moves, period_dates=period_dates)
        return budget_moves, reset_date_lines

    def _required_fields_to_commit(self):
        return [self._budget_analytic_field]

    def _init_docline_budget_vals(self, budget_vals, analytic_id):
        """To be extended by docline to add untaxed amount_currency"""
        if "amount_currency" not in budget_vals:
            raise ValidationError(self.env._("No amount_currency passed in!"))
        return budget_vals

    def _get_budget_company(self):
        """Company of the document of the line, whose budget settings apply,
        whatever the current company."""
        self.ensure_one()
        return self[self._doc_rel].company_id or self.env.company

    def _get_included_tax(self):
        """Taxes included in the budget of the line, when its company includes
        specific taxes. Extended by document line models."""
        return self.env["account.tax"]

    def _taxes_included(self, taxes):
        """Check configuration, both document and tax type"""
        company = self._get_budget_company()
        if not company.budget_include_tax:
            return False
        if company.budget_include_tax_method == "all":
            return taxes
        if company.budget_include_tax_method == "specific":
            return taxes & self._get_included_tax()
        return False

    def _get_budget_document_tax_mode(self):
        """Tax mode of the document of the line, if it has one: whether its
        prices include taxes, whatever the taxes say."""
        if "document_tax_mode" in self._fields:
            return self.document_tax_mode
        return None

    def _budget_include_tax(self, budget_vals):
        if "tax_ids" not in budget_vals:
            return budget_vals
        tax_ids = budget_vals.pop("tax_ids")
        if tax_ids:
            is_refund = False
            if self._name == "account.move.line" and self.move_id.move_type in (
                "in_refund",
                "out_refund",
            ):
                is_refund = True
            all_taxes = self.env["account.tax"].browse(tax_ids)
            document_tax_mode = self._get_budget_document_tax_mode()
            # For included taxes case
            included_taxes = self._taxes_included(all_taxes)
            if included_taxes:
                res = included_taxes.compute_all(
                    budget_vals["amount_currency"],
                    is_refund=is_refund,
                    document_tax_mode=document_tax_mode,
                )
                budget_vals["amount_currency"] = res["total_included"]
            else:
                res = all_taxes.compute_all(
                    budget_vals["amount_currency"],
                    is_refund=is_refund,
                    document_tax_mode=document_tax_mode,
                )
                budget_vals["amount_currency"] = res["total_excluded"]
        return budget_vals

    def prepare_commit(self):
        self.ensure_one()
        if self[
            self._doc_rel
        ].state not in self._no_date_commit_states or self.env.context.get(
            "force_commit"
        ):  # precommit case
            self._set_date_commit()
            if self.can_commit:  # Check only the can_commit lines
                self._check_date_commit()  # Testing only, can be removed when stable

    def _check_date_commit(self):
        """Commit date must inline with analytic account"""
        self.ensure_one()
        docline = self
        analytics = docline._convert_analytics()
        if analytics:
            if not docline.date_commit:
                raise UserError(self.env._("No budget commitment date"))
            for analytic in analytics:
                date_from = analytic.bm_date_from
                date_to = analytic.bm_date_to
                if (date_from and date_from > docline.date_commit) or (
                    date_to and date_to < docline.date_commit
                ):
                    raise UserError(
                        self.env._(
                            "Budget date commit is not within date range of - %s",
                            analytic.display_name,
                        )
                    )
        else:
            if docline.date_commit:
                raise UserError(self.env._("Budget commitment date not required"))

    def close_budget_move(self):
        """Reverse commit with amount_commit/date_commit to zero budget"""
        if not self.env.su and not self.env.user.has_group(
            "budget_control.group_budget_control_manager"
        ):
            raise AccessError(self.env._("Only budget managers can close budgets."))
        for docline in self:
            # Every row with an outstanding commitment
            rows = {
                key: 0.0
                for key, amount in (docline.amount_commit or {}).items()
                if amount
            }
            if not rows:
                continue
            docline.with_context(
                use_amount_commit=True,
                commit_note=self.env._("Auto adjustment on close budget"),
                adj_commit=True,
            ).commit_budget(reverse=True, analytic_distribution=rows)
