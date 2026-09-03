# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime
from json import dumps

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class BaseBudgetMove(models.AbstractModel):
    _name = "base.budget.move"
    _description = "Document Budget Moves"
    _budget_control_field = "account_id"
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
        related="template_line_id.kpi_id",
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
        string="Account",
        auto_join=True,
        index=True,
        readonly=True,
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Analytic Account",
        auto_join=True,
        index=True,
        readonly=True,
    )
    analytic_group = fields.Many2one(
        comodel_name="account.analytic.group",
        auto_join=True,
        index=True,
        readonly=True,
    )
    analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        string="Analytic Tags",
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
        string="Company",
        required=True,
        default=lambda self: self.env.user.company_id.id,
        index=True,
    )
    note = fields.Char(
        readonly=True,
    )
    adj_commit = fields.Boolean(
        help="This budget move line is the result of Over returned 'Automatic Adjustment'",
    )
    fwd_commit = fields.Boolean(
        help="This budget move line is the result of 'Forward Budget Commitment'",
    )

    def _compute_reference(self):
        """Compute reference name of the budget move document"""
        self.update({"reference": False})

    def _compute_source_document(self):
        """Compute source document of the budget move document"""
        self.update({"source_document": False})


class BudgetDoclineMixinBase(models.AbstractModel):
    _name = "budget.docline.mixin.base"
    _description = (
        "Base of budget.docline.mixin, used for non budgeting model extension"
    )
    _budget_analytic_field = "analytic_account_id"
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


class BudgetDoclineMixin(models.AbstractModel):
    _name = "budget.docline.mixin"
    _inherit = ["budget.docline.mixin.base"]
    _description = "Mixin used in each document line model that commit budget"

    can_commit = fields.Boolean(
        compute="_compute_can_commit",
        help="If True, this docline is eligible to create budget move",
    )
    amount_commit = fields.Float(
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
    fwd_analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Carry Forward Analytic",
        copy=False,
        readonly=False,
        index=True,
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
        return self.env.context.get("alt_budget_move_model") or self._budget_move_model

    def _budget_field(self):
        return self.env.context.get("alt_budget_move_field") or self._budget_move_field

    def _call_budget_method_guarded(self, method_name):
        """Call <method_name>() unless it's already in progress for this
        exact recordset higher up the current call stack (write() MRO can
        re-enter for the same records)."""
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
        raise ValidationError(_("No implementation error!"))

    @api.onchange("fwd_analytic_account_id")
    def _onchange_fwd_analytic_account_id(self):
        self.fwd_date_commit = self.fwd_analytic_account_id.bm_date_from

    @api.depends(lambda self: [self._budget_analytic_field])
    def _compute_auto_adjust_date_commit(self):
        for docline in self:
            docline.auto_adjust_date_commit = docline[
                self._budget_analytic_field
            ].auto_adjust_date_commit

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
            lambda l: l.analytic_account_id == analytic
        )

    @api.depends("budget_move_ids", "budget_move_ids.date")
    def _compute_commit(self):
        """
        - Calc amount_commit from all budget_move_ids
        - Calc date_commit if not exists and on 1st budget_move_ids only or False
        """
        for rec in self:
            debit = sum(rec.budget_move_ids.mapped("debit"))
            credit = sum(rec.budget_move_ids.mapped("credit"))
            rec.amount_commit = debit - credit
            if rec.budget_move_ids:
                rec.date_commit = min(rec.budget_move_ids.mapped("date"))
            else:
                rec.date_commit = rec.date_commit

    def _compute_json_budget_popover(self):
        FloatConverter = self.env["ir.qweb.field.float"]
        for rec in self:
            analytic = rec[self._budget_analytic_field]
            if not analytic:
                rec.json_budget_popover = False
                continue
            # Budget Period is required, even a False one
            budget_period = self.env["budget.period"]._get_eligible_budget_period(
                date=rec.date_commit
            )
            analytic = analytic.with_context(budget_period_ids=[budget_period.id])
            rec.json_budget_popover = dumps(
                {
                    "title": _("Budget Figure"),
                    "icon": "fa-info-circle",
                    "popoverTemplate": "budget_control.budgetPopOver",
                    "analytic": analytic.display_name,
                    "budget": FloatConverter.value_to_html(
                        analytic.amount_budget, {"decimal_precision": "Product Price"}
                    ),
                    "consumed": FloatConverter.value_to_html(
                        analytic.amount_consumed, {"decimal_precision": "Product Price"}
                    ),
                    "balance": FloatConverter.value_to_html(
                        analytic.amount_balance, {"decimal_precision": "Product Price"}
                    ),
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
            raise ValidationError(_("'_budget_date_commit_fields' is not set!"))
        analytic = docline[self._budget_analytic_field]
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

    def _update_budget_commitment(self, budget_vals, reverse=False):
        self.ensure_one()
        company = self.env.user.company_id
        account = self.account_id
        # Check params analytic_account_id, if not it should be self analytic
        analytic_account = budget_vals.get("analytic_account_id", False)
        if not analytic_account:
            analytic_account = self[self._budget_analytic_field]
        budget_moves = self[self._budget_field()]
        date_commit = budget_vals.get(
            "date",
            max(budget_moves.mapped("date")) if budget_moves else self.date_commit,
        )
        currency = hasattr(self, "currency_id") and self.currency_id or False
        amount = budget_vals["amount_currency"]  # init
        today = fields.Date.context_today(self)
        if (
            not self.env.context.get("use_amount_commit")
            and currency
            and currency != company.currency_id
        ):
            amount = self._get_amount_convert_currency(
                budget_vals["amount_currency"], currency, company, date_commit or today
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
            "analytic_account_id": analytic_account.id,
            "analytic_group": analytic_account.group_id.id,
            "date": date_commit or today,
            "amount_currency": budget_vals["amount_currency"],
            "debit": not reverse and amount or 0,
            "credit": reverse and amount or 0,
            "company_id": company.id,
        }
        if sum([res["debit"], res["credit"]]) < 0:
            res["debit"], res["credit"] = abs(res["credit"]), abs(res["debit"])
        budget_vals.update(res)
        return budget_vals

    def _update_template_line(self, budget_move):
        self.ensure_one()
        BudgetPeriod = self.env["budget.period"]
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
        return budget_move

    @api.model
    def _update_template_line_batch(self, budget_moves, period_dates=None):
        """Assign template/KPI once per period and account, instead of once
        per docline via _update_template_line. Behavior-equivalent because
        _update_template_line always resolves with need_control=True, which
        reduces _prepare_controls' gating to just budget_bypass + account_id.

        ``period_dates`` (``{move_id: date}``) lets a caller force the period
        lookup to use a different date than the move's own ``date`` field,
        needed when a reverse move's own date differs from the source
        docline's date_commit that _update_template_line() would have used.
        """
        if not budget_moves:
            return budget_moves
        period_dates = period_dates or {}
        BudgetPeriod = self.env["budget.period"]
        periods_by_date = {}
        grouped_move_ids = {}
        group_periods = {}
        for move in budget_moves:
            if move.account_id.budget_bypass or not move.account_id:
                continue
            period_date = period_dates.get(move.id, move.date)
            if period_date not in periods_by_date:
                periods_by_date[period_date] = BudgetPeriod._get_eligible_budget_period(
                    period_date
                )
            period = periods_by_date[period_date]
            if not period:
                continue
            key = (period.id, move.account_id.id)
            grouped_move_ids.setdefault(key, []).append(move.id)
            group_periods[key] = period
        for key, move_ids in grouped_move_ids.items():
            period = group_periods[key]
            template_lines = period.template_id.line_ids
            if not template_lines:
                continue
            template_line = BudgetPeriod._get_kpi_by_control_key(
                template_lines, {"account_id": key[1]}, budget_period=period
            )
            if template_line:
                budget_moves.browse(move_ids).write(
                    {"template_line_id": template_line.id}
                )
        return budget_moves

    def _get_domain_fwd_line(self, docline):
        return [
            ("res_model", "=", docline._name),
            ("res_id", "=", docline.id),
            ("forward_id.state", "=", "done"),
        ]

    def forward_commit(self):
        # allow all user can do it because this is common function
        self = self.sudo()
        ForwardLine = self.env["budget.commit.forward.line"]
        BudgetPeriod = self.env["budget.period"]
        for docline in self:
            if not docline.fwd_analytic_account_id or not docline.fwd_date_commit:
                continue
            if (
                docline[self._budget_analytic_field] == docline.fwd_analytic_account_id
                and docline.date_commit == docline.fwd_date_commit
            ):  # no forward to same date
                # docline.fwd_analytic_account_id = False
                # docline.fwd_date_commit = False
                continue
            domain_fwd_line = self._get_domain_fwd_line(docline)
            fwd_lines = ForwardLine.search(domain_fwd_line)
            # NOTE: this function will support commit forward more than 1 time
            # carry forward - get line with it self or other year
            if self.env.context.get("active_model") == "budget.commit.forward":
                active_id = self.env.context.get("active_id", False)
                fwd_lines.filtered(
                    lambda l: (
                        l.forward_id.state == "review" and l.forward_id.id == active_id
                    )
                    or l.forward_id.state == "done"
                )
            else:  # recompute budget
                fwd_lines.filtered(lambda l: l.forward_id.state == "done")
            for fwd_line in fwd_lines:
                # find last date of carry forward
                budget_period = BudgetPeriod._get_eligible_budget_period(
                    fwd_line.date_commit
                )
                # create commitment carry (credit)
                budget_move = docline.with_context(
                    use_amount_commit=True,
                    commit_note=_("Commitment carry forward"),
                    fwd_commit=True,
                    fwd_amount_commit=fwd_line.amount_commit,
                ).commit_budget(
                    reverse=True,
                    date=budget_period.bm_date_to,
                    analytic_account_id=fwd_line.analytic_account_id,
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
                        }
                    )
                # Remove forward commitment from unused subsequent year budget lines
                # If a budget line was forwarded to the next year but the budget
                # for that year is not utilized, this code removes the forward commitment,
                # allowing the line to be forwarded again in the following year.
                budget_move_previous_forward = self[self._budget_field()].filtered(
                    lambda l: l.fwd_commit
                    and l.date < fwd_line.forward_id.to_date_commit
                    and l.debit > 0.0
                )
                if budget_move_previous_forward:
                    budget_move_previous_forward.write({"fwd_commit": False})

    def _check_required_analytic(self):
        """Return True if analytic is required by policy but missing."""
        self.ensure_one()
        required_analytic = self.env.user.has_group(
            "budget_control.group_required_analytic"
        )
        # Required all document except move type entry or display_type is not false
        return bool(
            required_analytic
            and (hasattr(self, "display_type") and not self.display_type)
            and not self[self._budget_analytic_field]
            and not (
                self._name == "account.move.line" and self.move_id.move_type == "entry"
            )
            and not self._context.get("bypass_required_analytic")
        )

    def commit_budget(self, reverse=False, **vals):
        """Create budget commit for each docline"""
        if self._check_required_analytic():
            raise UserError(_("Please fill analytic account."))
        self.prepare_commit()
        to_commit = self.env.context.get("force_commit") or self._valid_commit_state()
        if self.can_commit and to_commit:
            budget_vals = self._prepare_commit_vals(reverse=reverse, **vals)
            if not budget_vals:
                return False
            budget_move = self.env[self._budget_model()].create(budget_vals)
            # Update Template Line
            budget_move = self._update_template_line(budget_move)
            if reverse:  # On reverse, make sure not over returned
                self.env["budget.period"].check_over_returned_budget(self)
            return budget_move
        else:
            self[self._budget_field()].unlink()

    def _prepare_commit_vals(self, reverse=False, **vals):
        """Return budget-move values without creating the record."""
        self.ensure_one()
        # Set amount_currency
        budget_vals = self._init_docline_budget_vals(vals)
        # Case budget_include_tax = True
        budget_vals = self._budget_include_tax(budget_vals)
        # Case force use_amount_commit, this should overwrite tax compute
        if self.env.context.get("use_amount_commit"):
            budget_vals["amount_currency"] = self.amount_commit
        if self.env.context.get("fwd_amount_commit"):
            budget_vals["amount_currency"] = self.env.context.get("fwd_amount_commit")
        # Only on case reverse, to force use return_amount_commit
        if reverse and "return_amount_commit" in self.env.context:
            budget_vals["amount_currency"] = self.env.context.get(
                "return_amount_commit"
            )
        # Complete budget commitment dict
        budget_vals = self._update_budget_commitment(budget_vals, reverse=reverse)
        # Final note
        budget_vals["note"] = self.env.context.get("commit_note")
        # Is Adjustment Commit
        budget_vals["adj_commit"] = self.env.context.get("adj_commit")
        # Is Forward Commit
        budget_vals["fwd_commit"] = self.env.context.get("fwd_commit")
        if not budget_vals["amount_currency"]:
            return None
        return budget_vals

    def prepare_commit_batch(self):
        """Batched version of prepare_commit()/_set_date_commit(): group the
        resulting date_commit writes so doclines sharing a date use one
        write() instead of one per docline."""
        eligible = self.filtered(
            lambda d: d[d._doc_rel].state not in d._no_date_commit_states
            or self.env.context.get("force_commit")
        )
        if not eligible:
            return eligible
        force_date_commit = self.env.context.get("force_date_commit")
        if not force_date_commit and not self._budget_date_commit_fields:
            raise ValidationError(_("'_budget_date_commit_fields' is not set!"))
        groups = {}
        for docline in eligible:
            analytic = docline[docline._budget_analytic_field]
            if force_date_commit:
                target_date = force_date_commit
            elif not analytic:
                target_date = False
            elif docline.date_commit:
                target_date = docline.date_commit
            else:
                target_date = docline._get_budget_date_commit(docline)
                if target_date:
                    target_date = fields.Date.to_date(target_date)
                if target_date and analytic.auto_adjust_date_commit:
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
        """Recreate commitments for a recordset with batched unlink/create/write,
        instead of unlink()+commit_budget() once per docline."""
        doclines = self
        doclines.mapped(doclines._budget_field()).unlink()
        for docline in doclines:
            if docline._check_required_analytic():
                raise UserError(_("Please fill analytic account."))
        doclines.prepare_commit_batch()

        to_commit = doclines.filtered(
            lambda d: d.can_commit
            and (self.env.context.get("force_commit") or d._valid_commit_state())
        )
        budget_vals_list = []
        for docline in to_commit:
            budget_vals = docline._prepare_commit_vals()
            if budget_vals:
                budget_vals_list.append(budget_vals)
        if not budget_vals_list:
            return self.env[doclines._budget_model()]
        budget_moves = self.env[doclines._budget_model()].create(budget_vals_list)
        return doclines._update_template_line_batch(budget_moves)

    def _can_batch_budget_precommit(self):
        """Opt in only when batch precommit matches commit_budget() semantics."""
        return False

    def _create_precommit_budget_moves_batch(self):
        """Batched replacement for check_budget_precommit()'s per-line
        `line.with_context(force_commit=True).commit_budget()` loop.

        force_commit=True makes prepare_commit()'s eligibility gate and
        commit_budget()'s to_commit always true, so the per-line outcome
        reduces to can_commit; this reproduces that with batched writes.
        """
        doclines = self.sudo()
        # Captured before any mutation below, matching the original's
        # inline-per-iteration capture (safe: no docline's commit here
        # affects another docline's date_commit).
        reset_date_lines = doclines.filtered(lambda line: not line.date_commit)
        force_doclines = doclines.with_context(force_commit=True)

        for line in force_doclines:
            if line._check_required_analytic():
                raise UserError(_("Please fill analytic account."))

        force_doclines.prepare_commit_batch()
        to_commit = force_doclines.filtered("can_commit")
        not_to_commit = force_doclines - to_commit
        if not_to_commit:
            not_to_commit.mapped(not_to_commit._budget_field()).unlink()

        budget_vals_list = []
        move_dates = []
        for line in to_commit:
            line_vals = line._prepare_commit_vals()
            if line_vals:
                budget_vals_list.append(line_vals)
                move_dates.append(line.date_commit)
        if not budget_vals_list:
            return self.env[force_doclines._budget_model()], reset_date_lines

        budget_moves = self.env[force_doclines._budget_model()].create(budget_vals_list)
        period_dates = dict(zip(budget_moves.ids, move_dates))
        to_commit._update_template_line_batch(budget_moves, period_dates=period_dates)
        return budget_moves, reset_date_lines

    def _required_fields_to_commit(self):
        return [self._budget_analytic_field]

    def _init_docline_budget_vals(self, budget_vals):
        """To be extended by docline to add untaxed amount_currency"""
        if "amount_currency" not in budget_vals:
            raise ValidationError(_("No amount_currency passed in!"))
        return budget_vals

    def _taxes_included(self, taxes):
        """Check configuration, both document and tax type"""
        if not self.env.company.budget_include_tax:
            return False
        else:
            if self.env.company.budget_include_tax_method == "all":
                return taxes
            if self.env.company.budget_include_tax_method == "specific":
                included_taxes = self._get_included_tax()
                return taxes & included_taxes
            return False

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
            # For included taxes case
            included_taxes = self._taxes_included(all_taxes)
            if included_taxes:
                res = included_taxes.compute_all(
                    budget_vals["amount_currency"], is_refund=is_refund
                )
                budget_vals["amount_currency"] = res["total_included"]
            else:
                res = all_taxes.compute_all(
                    budget_vals["amount_currency"], is_refund=is_refund
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
        analytic = docline[self._budget_analytic_field]
        if analytic:
            if not docline.date_commit:
                raise UserError(_("No budget commitment date"))
            date_from = analytic.bm_date_from
            date_to = analytic.bm_date_to
            if (date_from and date_from > docline.date_commit) or (
                date_to and date_to < docline.date_commit
            ):
                raise UserError(
                    _("Budget date commit is not within date range of - %s")
                    % analytic.display_name
                )
        else:
            if docline.date_commit:
                raise UserError(_("Budget commitment date not required"))

    def close_budget_move(self):
        """Reverse commit with amount_commit/date_commit to zero budget"""
        for docline in self:
            docline.with_context(
                use_amount_commit=True,
                commit_note=_("Auto adjustment on close budget"),
                adj_commit=True,
            ).commit_budget(
                reverse=True, analytic_account_id=docline.fwd_analytic_account_id
            )
