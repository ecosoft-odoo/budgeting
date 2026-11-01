# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import SQL, float_compare, format_amount


class BudgetPeriod(models.Model):
    _inherit = "budget.period"

    template_id = fields.Many2one(
        comodel_name="budget.template",
        string="Budget Template",
        ondelete="restrict",
        tracking=True,
    )
    control_budget = fields.Boolean(
        help="Block document transaction if budget is not enough",
        tracking=True,
    )
    account = fields.Boolean(
        string="On Account",
        compute="_compute_control_account",
        store=True,
        readonly=False,
        tracking=True,
        help="Control budget on journal document(s), i.e., vendor bill",
    )
    control_all_analytic_accounts = fields.Boolean(
        string="Control All Analytics",
        default=True,
        tracking=True,
    )
    control_analytic_account_ids = fields.Many2many(
        comodel_name="account.analytic.account",
        relation="budget_period_analytic_account_rel",
        string="Controlled Analytics",
        tracking=True,
    )
    control_level = fields.Selection(
        selection=[
            ("analytic", "Analytic"),
            ("analytic_kpi", "Analytic & KPI"),
        ],
        string="Level of Control",
        required=True,
        default="analytic",
        tracking=True,
        help="Level of budget check.\n"
        "1. Based on Analytic Account only\n"
        "2. Based on Analytic Account & KPI (more fine granied)",
    )
    plan_date_range_type_id = fields.Many2one(
        comodel_name="date.range.type",
        string="Plan Date Range",
        ondelete="restrict",
        tracking=True,
        help="Budget control sheet in this budget control year, will use this "
        "data range to plan the budget.",
    )
    unmatched_account_policy = fields.Selection(
        selection=[
            ("error", "Block (must be in template)"),
            ("skip", "Allow (pass through)"),
        ],
        default="error",
        required=True,
        tracking=True,
        help="Policy when a transaction account is not found in the budget template.\n"
        "- Block: raise an error (strict mode)\n"
        "- Allow: skip budget check and let the transaction pass through",
    )

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        res["template_id"] = self.env.company.budget_template_id.id
        return res

    @api.constrains(
        "budget_scope",
        "control_all_analytic_accounts",
        "control_analytic_account_ids",
    )
    def _check_lifetime_scope(self):
        for period in self.filtered(lambda rec: rec.budget_scope == "lifetime"):
            if period.control_all_analytic_accounts:
                raise ValidationError(
                    self.env._(
                        "A Lifetime Budget Period must be restricted to "
                        "one analytic account."
                    )
                )
            if len(period.control_analytic_account_ids) != 1:
                raise ValidationError(
                    self.env._(
                        "A Lifetime Budget Period must have exactly one "
                        "controlled analytic account."
                    )
                )
            duplicate = self.search(
                [
                    ("id", "!=", period.id),
                    ("budget_scope", "=", "lifetime"),
                    (
                        "control_analytic_account_ids",
                        "in",
                        period.control_analytic_account_ids.ids,
                    ),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    self.env._(
                        "Analytic %(analytic)s already has Lifetime Budget Period "
                        "%(period)s.",
                        analytic=period.control_analytic_account_ids.display_name,
                        period=duplicate.display_name,
                    )
                )

    @api.constrains(
        "control_budget", "account", "template_id", "plan_date_range_type_id"
    )
    def _check_budget_control_setup(self):
        """A period without control may serve other budget applications only
        (e.g. budget proposals), so the control setup is required on use."""
        for period in self.filtered(lambda rec: rec.control_budget or rec.account):
            if not period.template_id or not period.plan_date_range_type_id:
                raise ValidationError(
                    self.env._(
                        "Budget Period %(period)s needs a Budget Template and a "
                        "Plan Date Range to control budget.",
                        period=period.display_name,
                    )
                )

    @api.depends("control_budget")
    def _compute_control_account(self):
        for rec in self:
            rec.account = rec.control_budget

    @api.model
    def check_budget_constraint(self, budget_constraints, doclines):
        error_messages = []
        for budget_constraint in budget_constraints:
            # Run the server action associated with the budget constraint.
            # If it returns any error messages, add them to the list.
            msg_error = (
                budget_constraint.server_action_id.with_context(
                    active_model=budget_constraint._name,
                    active_id=budget_constraint.id,
                    doclines=doclines,
                )
                .sudo()
                .run()
            )
            if msg_error:
                error_messages.extend(msg_error)
        # If the loop completed without being interrupted, raise a UserError
        # with the concatenated error messages.
        if error_messages:
            raise UserError("\n".join(error_messages))
        return True

    def _get_budget_constraint(self):
        return self.env["budget.constraint"].search(
            [("active", "=", True)], order="sequence"
        )

    @api.model
    def _group_doclines_by_analytic(self, doclines):
        """Group document lines by each budget analytic of their distribution.

        A row of a distribution (``{"12,34": 100}``) charges at most one budget
        analytic, an account of a plan with Control Budget ticked; accounts of
        other plans are ignored.
        """
        grouped_line_ids = defaultdict(list)
        analytic_field = doclines._budget_analytic_field
        for line in doclines:
            distribution = line[analytic_field]
            line._check_budget_analytic_distribution(distribution)
            for analytic_id in sorted(line._get_budget_analytic_percents(distribution)):
                grouped_line_ids[analytic_id].append(line.id)
        return [
            (analytic_id, doclines.browse(line_ids))
            for analytic_id, line_ids in grouped_line_ids.items()
        ]

    @api.model
    def check_budget(self, doclines, doc_type="account"):
        """
        Check the budget based on the input budget moves, i.e., account_move_line.
        1. Get a valid budget period (how budget is being controlled).
        2. Determine which account (KPI) and analytic
            to control based on (1) and doclines.
        3. Check for negative budget and return warnings
            based on (2) and the KPI matrix.
        """
        if self.env.context.get("force_no_budget_check"):
            return
        doclines = doclines.filtered("can_commit")
        if not doclines:
            return
        BudgetPeriod = self.sudo()
        budget_constraints = BudgetPeriod._get_budget_constraint()

        # Check budget by group analytic. For case many budget periods in one document.
        # Pass 1: resolve each analytic account's group, no DB hit yet.
        groups = []
        period_cache = {}
        controls_cache = {}
        # Each document company checks the budget of its own periods
        company_groups = [
            (analytic_id, company, lines)
            for analytic_id, analytic_doclines in (
                BudgetPeriod._group_doclines_by_analytic(doclines)
            )
            for company, lines in analytic_doclines.grouped(
                lambda line: line[line._doc_rel].company_id
            ).items()
        ]
        for analytic_id, company, aa_doclines in company_groups:
            # Find active budget.period based on latest doclines date_commit
            date_commit = aa_doclines.filtered("date_commit").mapped("date_commit")
            if not date_commit:
                continue
            date_commit = max(date_commit)
            period_key = (analytic_id, date_commit, company.id)
            scoped_period = BudgetPeriod.with_company(company).with_context(
                budget_analytic_id=analytic_id
            )
            if period_key not in period_cache:
                period_cache[period_key] = scoped_period._get_eligible_budget_period(
                    date_commit, doc_type=doc_type
                )
            budget_period = period_cache[period_key]
            if not budget_period:
                continue
            # Find KPI controls only for this analytic. A line may contain several
            # analytics and consequently several budget moves.
            controls_key = (budget_period.id, analytic_id, tuple(aa_doclines.ids))
            if controls_key not in controls_cache:
                controls_cache[controls_key] = scoped_period._prepare_controls(
                    budget_period, aa_doclines
                )
            controls = [
                control
                for control in controls_cache[controls_key]
                if control["analytic_id"] == analytic_id
            ]
            if not controls:
                continue
            groups.append((aa_doclines, date_commit, budget_period, controls, company))
        if not groups:
            return
        # Validate each period's analytics in one query before the monitor scan.
        analytic_ids_by_period = defaultdict(set)
        for _doclines, _date, budget_period, controls, _company in groups:
            analytic_ids_by_period[budget_period.id].update(
                control["analytic_id"] for control in controls
            )
        for budget_period_id, analytic_ids in analytic_ids_by_period.items():
            BudgetPeriod.env["account.analytic.account"].browse(
                sorted(analytic_ids)
            )._check_budget_control_status(budget_period_id=budget_period_id)
        # Pass 2: one shared prefetch instead of one scan per control.
        all_controls = [c for group in groups for c in group[3]]
        avail_cache = BudgetPeriod._prefetch_budget_available(all_controls)
        BudgetPeriod = BudgetPeriod.with_context(_budget_avail_cache=avail_cache)
        for aa_doclines, date_commit, budget_period, controls, company in groups:
            CompanyPeriod = BudgetPeriod.with_company(company)
            # Check budget on each control element against each KPI/avail (period)
            currency = (
                "currency_id" in aa_doclines
                and aa_doclines.mapped("currency_id")[:1]
                or CompanyPeriod.env.context.get(
                    "doc_currency", CompanyPeriod.env.company.currency_id
                )
            )
            warnings = CompanyPeriod.with_context(
                date_commit=date_commit, doc_currency=currency, doclines=aa_doclines
            )._check_budget_available(controls, budget_period)
            if warnings:
                msg = "\n".join(["Budget not sufficient,", "\n".join(warnings)])
                raise UserError(msg)
            # Check budget constraint following your customize condition
            elif aa_doclines and budget_constraints and budget_period:
                CompanyPeriod.check_budget_constraint(budget_constraints, aa_doclines)
        return

    @api.model
    def check_budget_precommit(self, doclines, doc_type="account"):
        """Precommit check,
        first do the normal commit, do checking, and remove commits"""
        if not doclines:
            return
        doclines = doclines.sudo()
        # Allow precommit budget with related origin document (PO)
        budget_moves_uncommit = False
        if doc_type == "account":
            budget_moves_uncommit = doclines.with_context(
                force_commit=True
            ).uncommit_purchase_budget()
        # Batch only models that explicitly guarantee equivalence with their
        # commit_budget() behavior. Other models keep the original line loop.
        if doclines._can_batch_budget_precommit():
            budget_moves, reset_date_lines = (
                doclines._create_precommit_budget_moves_batch()
            )
            budget_move_groups = [budget_moves]
        else:
            budget_move_groups = []
            reset_date_lines = doclines.filtered(lambda line: not line.date_commit)
            for line in doclines:
                budget_move = line.with_context(force_commit=True).commit_budget()
                if budget_move:
                    budget_move_groups.append(budget_move)
        # Update database, so we can check budget with query.
        flushed_models = set()
        for budget_moves in budget_move_groups:
            if budget_moves and budget_moves._name not in flushed_models:
                budget_moves.flush_model()
                flushed_models.add(budget_moves._name)
        # Check Budget
        self.env["budget.period"].check_budget(doclines, doc_type=doc_type)
        # Remove commits
        for budget_moves in budget_move_groups:
            budget_moves.unlink()
        # Delete date commit from system create auto only
        reset_date_lines.write({"date_commit": False})
        # Remove uncommit budget
        if budget_moves_uncommit:
            budget_moves_uncommit.unlink()

    @api.model
    def check_over_returned_budget(self, docline, reverse=False):
        """Adjust the analytic rows of ``docline`` whose commitment is over
        returned, back to zero."""
        sign = 1 if reverse else -1
        rows = {
            key: 0.0
            for key, amount in (docline.amount_commit or {}).items()
            if float_compare(sign * amount, 0.0, 2) == 1
        }
        if not rows:
            return
        # Reverse the outstanding balances, not the amounts being returned
        ctx = {
            key: value
            for key, value in docline.env.context.items()
            if key not in ("return_amount_commit", "fwd_amount_commit")
        }
        docline.with_context(
            ctx,
            use_amount_commit=True,
            commit_note=self.env._(
                "Over returned auto adjustment, %s", docline.display_name
            ),
            adj_commit=True,
        ).commit_budget(reverse=True, analytic_distribution=rows)

    @api.model
    def _get_eligible_budget_period(self, date=False, doc_type=False):
        """
        Get the eligible budget period based on the specified date and document type.
        """
        if not date:
            date = fields.Date.context_today(self)
        date = fields.Date.to_date(date)
        BudgetPeriod = self.env["budget.period"]
        analytic = self.env["account.analytic.account"]
        analytic_id = self.env.context.get("budget_analytic_id")
        if analytic_id:
            analytic = analytic.browse(analytic_id).exists()

        if analytic and analytic.budget_control_scope == "lifetime":
            budget_period = analytic.budget_period_id.filtered(
                lambda period: (
                    period.budget_scope == "lifetime"
                    and period.bm_date_from <= date <= period.bm_date_to
                    and (
                        not period.company_ids
                        or self.env.company.parent_ids & period.company_ids
                    )
                )
            )
        else:
            budget_period = BudgetPeriod._get_fiscal_period(date)
        if not doc_type:
            return budget_period
        # Get period control budget.
        # if doctype is account, check special control too.
        if doc_type == "account":
            return budget_period.filtered(
                lambda bp: (
                    (bp.control_budget and bp.account)
                    or (not bp.control_budget and bp.account)
                )
            )
        # Other module control budget must hook it for filter
        return budget_period

    @api.model
    def _get_control_budget_moves(self, budget_period, doclines):
        """Budget moves of ``doclines`` that ``budget_period`` checks: in the
        period, of the analytic of context ``budget_analytic_id`` if any, and
        not on accounts bypassing the budget."""
        analytic_id = self.env.context.get("budget_analytic_id")
        return doclines.mapped(doclines._budget_field()).filtered(
            lambda move: (
                (not analytic_id or move.analytic_account_id.id == analytic_id)
                and budget_period.bm_date_from <= move.date <= budget_period.bm_date_to
                and not move.account_id.budget_bypass
            )
        )

    @api.model
    def _prepare_controls(self, budget_period, doclines):
        controls = set()
        control_analytics = budget_period.control_analytic_account_ids
        budget_control_key = self.env.company.budget_control_key
        need_control = self.env.context.get("need_control")
        for budget_move in self._get_control_budget_moves(budget_period, doclines):
            if budget_period.control_all_analytic_accounts:
                if budget_move.analytic_account_id and budget_move[budget_control_key]:
                    controls.add(
                        (
                            budget_move.analytic_account_id.id,
                            budget_move[budget_control_key].id,
                        )
                    )
            else:  # analytic in control or force control by send context
                if (
                    budget_move.analytic_account_id in control_analytics
                    and budget_move[budget_control_key]
                ) or need_control:
                    controls.add(
                        (
                            budget_move.analytic_account_id.id,
                            budget_move[budget_control_key].id,
                        )
                    )
        # Convert to list of dicts for readability
        return [{"analytic_id": x[0], budget_control_key: x[1]} for x in controls]

    def _get_filter_template_line(self, all_template_lines, control):
        budget_control_key = self.env.company.budget_control_key
        if budget_control_key == "account_id":
            control_id = control[budget_control_key]
            template_lines = all_template_lines.filtered(
                lambda line, control_id=control_id: control_id in line.account_ids.ids
            )
        return template_lines

    def _get_control_key_obj(self, control_key, control_id):
        if control_key == "account_id":
            control = self.env["account.account"].browse(control_id)
            control_name = "account code"
        return control, control_name

    @api.model
    def _get_kpi_by_control_key(self, template_lines, control, budget_period=None):
        """
        By default, control key is account_id as it can be used to get KPI
        In future, this can be other key, i.e., activity_id based on installed module
        """
        control_key = self.env.company.budget_control_key
        control_id = control[control_key]
        template_line = self._get_filter_template_line(template_lines, control)
        if len(template_line) == 1:
            return template_line
        # Invalid Template Lines
        control, control_name = self._get_control_key_obj(control_key, control_id)
        if not template_line:
            if budget_period and budget_period.unmatched_account_policy == "skip":
                return self.env["budget.template.line"]
            raise UserError(
                self.env._(
                    "Chosen %(control_name)s %(control)s is not valid in template",
                    control_name=control_name,
                    control=control.display_name,
                )
            )
        raise UserError(
            self.env._(
                "Template Lines has more than one KPI being "
                "referenced by the same %(control_name)s %(control)s",
                control_name=control_name,
                control=control.display_name,
            )
        )

    def _get_where_domain(self, analytic_id, template_lines):
        """Return the WHERE clause (an SQL object) of the budget monitoring
        query."""
        where = SQL("analytic_account_id = %s", analytic_id)
        if (
            not template_lines
            or self.env.context.get("control_level", False) == "analytic"
        ):
            return where
        return SQL("%s AND kpi_id IN %s", where, tuple(template_lines.kpi_id.ids))

    def _get_budget_monitor_report(self):
        """Hook for add context"""
        return self.env["budget.monitor.report"]

    def _can_use_budget_available_cache(self, template_lines):
        """Whether the shared cache represents this availability query.

        Extensions adding dimensions to ``_get_where_domain()`` should override
        this hook and return ``False`` for template-line models that need those
        extra filters.
        """
        return not template_lines or template_lines._name == "budget.template.line"

    def _prefetch_budget_available(self, controls):
        """One monitor-report scan for all controls' analytic accounts, summed
        per KPI, period and amount type and keyed by analytic_id.
        ``check_budget()`` can then serve every control from this dict instead
        of running one SQL query per control.

        Only the base filter shape (``analytic_account_id IN (...)``) is
        served here; ``_get_where_domain()`` overrides that add extra clauses
        (e.g. budget_plan_detail's ``fund_id``) are not covered and must keep
        using the per-control ``_get_budget_avaiable()`` path.
        """
        analytic_ids = sorted(
            {c["analytic_id"] for c in controls if c.get("analytic_id")}
        )
        if not analytic_ids:
            return {}
        self.env.flush_all()
        report_sql = self._get_budget_monitor_report()._table_sql
        self.env.cr.execute(
            SQL(
                """
                    SELECT
                        analytic_account_id,
                        kpi_id,
                        budget_period_id,
                        amount_type,
                        SUM(amount) AS amount
                    FROM %s report
                    WHERE analytic_account_id IN %s
                    GROUP BY
                        analytic_account_id, kpi_id, budget_period_id, amount_type
                """,
                report_sql,
                tuple(analytic_ids),
            )
        )
        cache = {}
        for row in self.env.cr.dictfetchall():
            cache.setdefault(row["analytic_account_id"], []).append(row)
        return cache

    def _get_budget_avaiable(self, analytic_id, template_lines):
        # Callers that batch many queries can set env.context['skip_budget_flush']
        # after flushing once themselves, avoiding a flush_all() per control.
        # check_budget() additionally pre-scans every analytic once and passes
        # the rows through env.context['_budget_avail_cache']; we then filter
        # by kpi_id in Python when control_level != "analytic".
        cache = self.env.context.get("_budget_avail_cache")
        # The cache only covers the base filter shape; custom _get_where_domain
        # overrides (e.g. budget_plan_detail's fund_id) fall through to a query.
        if cache is not None and self._can_use_budget_available_cache(template_lines):
            rows = cache.get(analytic_id, [])
            if (
                template_lines
                and self.env.context.get("control_level", False) != "analytic"
            ):
                kpi_ids = set(template_lines.kpi_id.ids)
                rows = [r for r in rows if r.get("kpi_id") in kpi_ids]
            return rows
        if not self.env.context.get("skip_budget_flush"):
            self.env.flush_all()
        self.env.cr.execute(
            SQL(
                """
                    SELECT *
                    FROM %s report
                    WHERE %s
                """,
                self._get_budget_monitor_report()._table_sql,
                self._get_where_domain(analytic_id, template_lines),
            )
        )
        return self.env.cr.dictfetchall()

    def _get_balance_currency(self, company, balance, doc_currency, date_commit):
        """Convert balance to balance currency (multi-currency)"""
        return company.currency_id._convert(balance, doc_currency, company, date_commit)

    @api.model
    def _check_budget_available(self, controls, budget_period):
        """
        This function is a CORE function, please modify carefully
        Author: Kitti U., Saran Lim.
        """
        warnings = []
        Analytic = self.env["account.analytic.account"]
        template_lines = all_template_lines = budget_period.template_id.line_ids
        company = self.env.company
        doc_currency = self.env.context.get("doc_currency")
        date_commit = self.env.context.get("date_commit")
        # A shared cache is built only after flushing, and nothing is written
        # while the control groups are checked. Without a cache, flush once here
        # before the per-control fallback queries.
        if self.env.context.get("_budget_avail_cache") is None:
            self.env.flush_all()
        BudgetPeriod = self.with_context(skip_budget_flush=True)
        for control in controls:
            analytic_id = control["analytic_id"]
            # Get the KPI(s) to check the budget,
            # in case the control level is set to "analytic_kpi"
            if budget_period.control_level == "analytic_kpi":
                template_lines = BudgetPeriod._get_filter_template_line(
                    all_template_lines, control
                )
                if (
                    not template_lines
                    and budget_period.unmatched_account_policy == "skip"
                ):
                    continue
            # Get the available budget for the specified analytic account and KPI(s)
            query_data = BudgetPeriod.with_context(
                control_level=budget_period.control_level
            )._get_budget_avaiable(analytic_id, template_lines)
            # Check kpi not valid for budgeting when control level analytic & kpi
            data_budget = any(
                query["amount_type"] == "10_budget" for query in query_data
            )
            if budget_period.control_level == "analytic_kpi" and not data_budget:
                raise UserError(
                    BudgetPeriod.env._(
                        "Chosen KPI %s is not valid for budgeting",
                        template_lines.display_name,
                    )
                )
            balance = sum(
                q["amount"]
                for q in query_data
                if q["amount"] is not None and q["budget_period_id"] == budget_period.id
            )
            # Show a warning if the budget is not sufficient
            if (
                float_compare(
                    balance,
                    0.0,
                    precision_rounding=company.currency_id.rounding,
                )
                == -1
            ):
                # Convert the balance to the document currency
                balance_currency = BudgetPeriod._get_balance_currency(
                    company, balance, doc_currency, date_commit
                )
                fomatted_balance = format_amount(
                    BudgetPeriod.env, balance_currency, doc_currency
                )
                analytic_name = Analytic.browse(analytic_id).display_name
                if budget_period.control_level == "analytic_kpi":
                    analytic_name = f"{template_lines.display_name} & {analytic_name}"
                warnings.append(
                    BudgetPeriod.env._(
                        "%(analytic_name)s, will result in %(formatted_balance)s",
                        analytic_name=analytic_name,
                        formatted_balance=fomatted_balance,
                    )
                )
        return list(set(warnings))

    @api.model
    def get_budget_info_from_dataset(self, query, dataset):
        """Get budget overview from a budget monitor dataset, i.e.,
        budget_info = {
            "amount_budget": 100,
            "amount_actual": 70,
            "amount_balance": 30
        }
        Note: based on installed modules
        """
        budget_info = dict.fromkeys(query["info_cols"], 0)
        budget_info["amount_commit"] = 0
        for col, (amount_type, is_commit) in query["info_cols"].items():
            info = list(
                filter(
                    lambda dataset, amount_type=amount_type: (
                        dataset["amount_type"] == amount_type
                    ),
                    dataset,
                )
            )
            if len(info) > 1:
                raise ValidationError(self.env._("Error retrieving budget info!"))
            if not info:
                continue
            amount = info[0]["amount"]
            if is_commit:
                budget_info[col] = -amount  # Negate
                budget_info["amount_commit"] += budget_info[col]
            elif amount_type == "12_forward_out":
                # The monitoring dataset stores outflows as negative ledger
                # amounts. Present Forward Out as a positive business amount.
                budget_info[col] = -amount
            elif amount_type == "80_actual":  # Negate consumed
                budget_info[col] = -amount
            else:
                budget_info[col] = amount
        budget_info["amount_consumed"] = (
            budget_info["amount_commit"] + budget_info["amount_actual"]
        )
        budget_info["amount_balance"] = (
            budget_info["amount_budget"]
            - budget_info["amount_forward_out"]
            - budget_info["amount_consumed"]
        )
        return budget_info

    def _budget_info_query(self):
        query = {
            "info_cols": {
                "amount_budget": (
                    "10_budget",
                    False,
                ),  # (amount_type, is_commit)
                "amount_forward_out": ("12_forward_out", False),
                "amount_actual": ("80_actual", False),
            },
            "fields": [
                "analytic_account_id",
                "budget_period_id",
                "amount_type",
                "amount",
            ],
            "groupby": [
                "analytic_account_id",
                "budget_period_id",
                "amount_type",
            ],
        }
        return query
