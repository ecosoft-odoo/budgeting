# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime
from json import dumps

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


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
    analytic_plan = fields.Many2one(
        comodel_name="account.analytic.plan",
        auto_join=True,
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
        string="Company",
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

    def _convert_analytics(self, analytic_distribution=False):
        Analytic = self.env["account.analytic.account"]
        analytics = analytic_distribution or self[self._budget_analytic_field]
        if not analytics:
            return Analytic
        # Check analytic from distribution it send data with JSON type 'dict'
        # and we need convert it to analytic object
        if self._budget_analytic_field == "analytic_distribution":
            account_analytic_ids = [
                int(v) for k in analytics.keys() for v in k.split(",")
            ]
            analytics = Analytic.browse(account_analytic_ids)
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
        return self.env.context.get("alt_budget_move_model") or self._budget_move_model

    def _budget_field(self):
        return self.env.context.get("alt_budget_move_field") or self._budget_move_field

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
        - Calc amount_commit from all budget_move_ids
        - Calc date_commit if not exists and on 1st budget_move_ids only or False
        """
        analytic_field = self._budget_analytic_field
        for rec in self:
            analytic_distribution = rec[analytic_field]
            # Add analytic_distribution from forward_commit
            if rec.fwd_analytic_distribution:
                for analytic_id, aa_percent in rec.fwd_analytic_distribution.items():
                    analytic_distribution[analytic_id] = aa_percent

            if not analytic_distribution:
                continue
            # Compute amount commit each analytic
            amount_commit_json = {}
            analytic_ids = {
                int(aa)
                for analytic in analytic_distribution
                for aa in analytic.split(",")
            }
            budget_moves = rec.budget_move_ids.filtered(
                lambda move, analytic_ids=analytic_ids: move.analytic_account_id.id
                in analytic_ids
            )

            for analytic_id in analytic_ids:
                filtered_moves = budget_moves.filtered(
                    lambda move, analytic_id=analytic_id: move.analytic_account_id.id
                    == analytic_id
                )
                amount_commit_json[str(analytic_id)] = sum(
                    filtered_moves.mapped("debit")
                ) - sum(filtered_moves.mapped("credit"))
            rec.amount_commit = amount_commit_json

            # Compute date commit
            if rec.budget_move_ids:
                rec.date_commit = min(rec.budget_move_ids.mapped("date"))

    def _compute_json_budget_popover(self):
        FloatConverter = self.env["ir.qweb.field.float"]
        for rec in self:
            analytic_distribution = rec[self._budget_analytic_field]
            analytic_account = rec._convert_analytics(
                analytic_distribution=analytic_distribution
            )
            if not analytic_account:
                rec.json_budget_popover = False
                continue
            # Budget Period is required, even a False one
            budget_period = self.env["budget.period"]._get_eligible_budget_period(
                date=rec.date_commit
            )
            rec.json_budget_popover = dumps(
                {
                    "title": self.env._("Budget Figure"),
                    "icon": "fa-info-circle",
                    "popoverTemplate": "budget_control.budgetPopOver",
                    "analytic": [
                        {
                            "id": aa.id,
                            "name": aa.display_name,
                            "budget": FloatConverter.value_to_html(
                                aa.amount_budget, {"decimal_precision": "Product Price"}
                            ),
                            "consumed": FloatConverter.value_to_html(
                                aa.amount_consumed,
                                {"decimal_precision": "Product Price"},
                            ),
                            "balance": FloatConverter.value_to_html(
                                aa.amount_balance,
                                {"decimal_precision": "Product Price"},
                            ),
                        }
                        for aa in analytic_account.with_context(
                            budget_period_ids=[budget_period.id]
                        )
                    ],
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

    def _get_analytic_budget_currency(self, analytic, date_commit):
        """Return the currency_id of the active budget control
        for analytic at date_commit."""
        BudgetPeriod = self.env["budget.period"]
        period = BudgetPeriod._get_eligible_budget_period(date=date_commit)
        if not period:
            return self.env["res.currency"]
        bc = (
            self.env["budget.control"]
            .sudo()
            .search(
                [
                    ("analytic_account_id", "=", analytic.id),
                    ("budget_period_id", "=", period.id),
                    ("state", "=", "done"),
                ],
                limit=1,
            )
        )
        return bc.currency_id

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
        # Block cross-currency commits: document company currency must match
        # the budget control currency to prevent incorrect budget consumption.
        bc_currency = self._get_analytic_budget_currency(analytic, date_commit or today)
        if bc_currency and bc_currency != document_company.currency_id:
            raise UserError(
                self.env._(
                    f"Company {document_company.name} "
                    f"({document_company.currency_id.name}) cannot commit to a "
                    f"{bc_currency.name} budget. "
                    "All companies sharing a budget must use the same currency.",
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
        control_key = self.env.company.budget_control_key
        periods_by_date = {}
        grouped_move_ids = {}
        group_periods = {}

        for move in budget_moves:
            if move.account_id.budget_bypass or not move[control_key]:
                continue
            period_date = period_dates.get(move.id, move.date)
            if period_date not in periods_by_date:
                periods_by_date[period_date] = BudgetPeriod._get_eligible_budget_period(
                    period_date
                )
            period = periods_by_date[period_date]
            if not period:
                continue
            key = (period.id, move[control_key].id)
            grouped_move_ids.setdefault(key, []).append(move.id)
            group_periods[key] = period

        for key, move_ids in grouped_move_ids.items():
            period = group_periods[key]
            template_lines = period.template_id.line_ids
            if not template_lines:
                continue
            template_line = BudgetPeriod._get_kpi_by_control_key(
                template_lines,
                {control_key: key[1]},
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

    def forward_commit(self):
        # allow all user can do it because this is common function
        self = self.sudo()
        ForwardLine = self.env["budget.commit.forward.line"]
        BudgetPeriod = self.env["budget.period"]
        for docline in self:
            if not docline.fwd_analytic_distribution or not docline.fwd_date_commit:
                continue
            if (
                docline[self._budget_analytic_field]
                == docline.fwd_analytic_distribution
                and docline.date_commit == docline.fwd_date_commit
            ):  # no forward to same date
                continue
            domain_fwd_line = self._get_domain_fwd_line(docline)
            fwd_lines = ForwardLine.search(domain_fwd_line)
            # NOTE: this function will support commit forward more than 1 time
            # carry forward - get line with it self or other year
            if self.env.context.get("active_model") == "budget.commit.forward":
                active_id = self.env.context.get("active_id", False)
                fwd_lines.filtered(
                    lambda line, active_id=active_id: (
                        line.forward_id.state == "review"
                        and line.forward_id.id == active_id
                    )
                    or line.forward_id.state == "done"
                )
            else:  # recompute budget
                fwd_lines.filtered(lambda line: line.forward_id.state == "done")
            for fwd_line in fwd_lines:
                # find last date of carry forward
                budget_period = BudgetPeriod._get_eligible_budget_period(
                    fwd_line.date_commit
                )
                # create commitment carry (credit)
                budget_move = docline.with_context(
                    use_amount_commit=True,
                    commit_note=self.env._("Commitment carry forward"),
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
                # for that year is not utilized,
                # this code removes the forward commitment,
                # allowing the line to be forwarded again in the following year.
                budget_move_previous_forward = self[self._budget_field()].filtered(
                    lambda line, fwd_line=fwd_line: line.fwd_commit
                    and line.date < fwd_line.forward_id.to_date_commit
                    and line.debit > 0.0
                )
                if budget_move_previous_forward:
                    budget_move_previous_forward.write({"fwd_commit": False})

    def _check_required_analytic(self):
        """
        Required all document except
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
            and not self[self._budget_analytic_field]
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
        if self._check_required_analytic():
            raise UserError(self.env._("Please fill analytic account."))
        self.prepare_commit()
        to_commit = self.env.context.get("force_commit") or self._valid_commit_state()
        if self.can_commit and to_commit:
            budget_commit_vals = self._prepare_commit_vals(reverse=reverse, **vals)
            if not budget_commit_vals:
                return False
            budget_move = self.env[self._budget_model()].create(budget_commit_vals)
            # Update Template Line
            budget_move = self._update_template_line(budget_move)
            if reverse:  # On reverse, make sure not over returned
                self.env["budget.period"].check_over_returned_budget(self)
            return budget_move
        else:
            self[self._budget_field()].unlink()

    def _prepare_commit_vals(self, reverse=False, **vals):
        """Return budget-move values without creating records."""
        self.ensure_one()
        budget_commit_vals = []
        if vals.get("analytic_account_id", False):
            analytic_accounts = vals["analytic_account_id"]
        else:
            analytic_accounts = self._convert_analytics(
                analytic_distribution=vals.get("analytic_distribution", False)
            )
            if vals.get("analytic_distribution", "/") != "/":
                del vals["analytic_distribution"]

        for analytic in analytic_accounts:
            budget_vals = self._init_docline_budget_vals(vals, analytic.id)
            budget_vals = self._budget_include_tax(budget_vals)
            if self.env.context.get("use_amount_commit"):
                budget_vals["amount_currency"] = self.amount_commit[str(analytic.id)]
            if self.env.context.get("fwd_amount_commit"):
                budget_vals["amount_currency"] = self.env.context["fwd_amount_commit"]
            if reverse and "return_amount_commit" in self.env.context:
                budget_vals["amount_currency"] = self.env.context[
                    "return_amount_commit"
                ]
            budget_vals = self._update_budget_commitment(
                budget_vals, analytic, reverse=reverse
            )
            budget_vals.update(
                {
                    "note": self.env.context.get("commit_note"),
                    "adj_commit": self.env.context.get("adj_commit"),
                    "fwd_commit": self.env.context.get("fwd_commit"),
                }
            )
            if not budget_vals["amount_currency"]:
                continue
            budget_commit_vals.append(budget_vals.copy())
            del budget_vals["amount_currency"]
        return budget_commit_vals

    def prepare_commit_batch(self, preserved_dates=None):
        """Set commitment dates in grouped writes, then validate each line."""
        preserved_dates = preserved_dates or {}
        force_date = self.env.context.get("force_date_commit")
        if force_date:
            force_date = fields.Date.to_date(force_date)
        eligible = self.filtered(
            lambda line: line[line._doc_rel].state not in line._no_date_commit_states
            or self.env.context.get("force_commit")
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
        doclines.mapped(doclines._budget_field()).unlink()
        for docline in doclines:
            if docline._check_required_analytic():
                raise UserError(self.env._("Please fill analytic account."))
        doclines.prepare_commit_batch(preserved_dates=preserved_dates)

        to_commit = doclines.filtered(
            lambda line: line.can_commit
            and (self.env.context.get("force_commit") or line._valid_commit_state())
        )
        budget_vals = []
        for docline in to_commit:
            budget_vals.extend(docline._prepare_commit_vals())
        if not budget_vals:
            return self.env[doclines._budget_model()]
        budget_moves = self.env[doclines._budget_model()].create(budget_vals)
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
        for line in to_commit:
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
                            "Budget date commit is not within date range of - %s"
                        )
                        % analytic.display_name
                    )
        else:
            if docline.date_commit:
                raise UserError(self.env._("Budget commitment date not required"))

    def close_budget_move(self):
        """Reverse commit with amount_commit/date_commit to zero budget"""
        for docline in self:
            docline.with_context(
                use_amount_commit=True,
                commit_note=self.env._("Auto adjustment on close budget"),
                adj_commit=True,
            ).commit_budget(
                reverse=True, analytic_distribution=docline.fwd_analytic_distribution
            )
