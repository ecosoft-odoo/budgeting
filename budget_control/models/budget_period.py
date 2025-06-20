# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import SQL, float_compare, format_amount


class BudgetPeriod(models.Model):
    _name = "budget.period"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "For each fiscal year, manage how budget is controlled"

    name = fields.Char(required=True, tracking=True)
    bm_date_from = fields.Date(
        string="Date From",
        required=True,
        tracking=True,
    )
    bm_date_to = fields.Date(
        string="Date To",
        required=True,
        tracking=True,
    )
    template_id = fields.Many2one(
        comodel_name="budget.template",
        string="Budget Template",
        ondelete="restrict",
        required=True,
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
        required=True,
        tracking=True,
        help="Budget control sheet in this budget control year, will use this "
        "data range to plan the budget.",
    )
    # analytic_ids = fields.One2many(
    #     comodel_name="account.analytic.account",
    #     inverse_name="budget_period_id",
    # )

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        res["template_id"] = self.env.company.budget_template_id.id
        return res

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
        else:
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
    def check_budget(self, doclines, doc_type="account"):
        """
        Check the budget based on the input budget moves, i.e., account_move_line.
        1. Get a valid budget period (how budget is being controlled).
        2. Determine which account (KPI) and analytic
            to control based on (1) and doclines.
        3. Check for negative budget and return warnings
            based on (2) and the KPI matrix.
        """
        if self._context.get("force_no_budget_check"):
            return
        doclines = doclines.filtered("can_commit")
        if not doclines:
            return
        self = self.sudo()
        budget_constraints = self._get_budget_constraint()
        all_analytics = doclines.mapped(doclines._budget_analytic_field)

        # Get All Analytic Account
        all_analytic_ids = set()
        for data_dict in all_analytics:
            # Check percent analytic account must be 100% only
            total_sum = sum(data_dict.values())
            if (
                float_compare(
                    total_sum,
                    100.0,
                    precision_rounding=2,
                )
                != 0
            ):
                raise UserError(
                    self.env._(
                        "The total sum percent of Analytic Account must 100%. "
                        "Please check again."
                    )
                )
            all_analytic_ids.update(
                int(aa) for key in data_dict.keys() for aa in key.split(",")
            )

        # Check budget by group analytic. For case many budget periods in one document.
        for aa in all_analytic_ids:
            if isinstance(aa, int):
                doclines = doclines.filtered(
                    lambda line, aa=aa, doclines=doclines: line[
                        doclines._budget_analytic_field
                    ].get(str(aa))
                )
            else:
                doclines = doclines.filtered(
                    lambda line, aa=aa, doclines=doclines: line[
                        doclines._budget_analytic_field
                    ]
                    == aa
                )
            # Find active budget.period based on latest doclines date_commit
            date_commit = doclines.filtered("date_commit").mapped("date_commit")
            if not date_commit:
                return
            date_commit = max(date_commit)
            budget_period = self._get_eligible_budget_period(
                date_commit, doc_type=doc_type
            )
            if not budget_period:
                return
            # Find combination of account (KPI) + analytic (i.e., project) to control
            controls = self._prepare_controls(budget_period, doclines)
            if not controls:
                return
            # The budget_control of these analytics must be active
            if isinstance(aa, int):
                analytic_ids = all_analytic_ids
            else:
                analytic_ids = [x["analytic_id"] for x in controls]
            analytics = self.env["account.analytic.account"].browse(analytic_ids)
            analytics._check_budget_control_status(budget_period_id=budget_period.id)
            # Check budget on each control element against each KPI/avail (period)
            currency = (
                "currency_id" in doclines
                and doclines.mapped("currency_id")[:1]
                or self.env.context.get("doc_currency", self.env.company.currency_id)
            )
            warnings = self.with_context(
                date_commit=date_commit, doc_currency=currency, doclines=doclines
            )._check_budget_available(controls, budget_period)
            if warnings:
                msg = "\n".join(["Budget not sufficient,", "\n".join(warnings)])
                raise UserError(msg)
            # Check budget constraint following your customize condition
            elif doclines and budget_constraints and budget_period:
                self.check_budget_constraint(budget_constraints, doclines)
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
        # Commit budget
        budget_moves = []
        vals_date_commit = []
        for line in doclines:
            if not line.date_commit:
                vals_date_commit.append(line.id)
            budget_move = line.with_context(force_commit=True).commit_budget()
            if budget_move:
                budget_moves.append(budget_move)
        # Update database, so we can check budget with query
        if budget_move:
            budget_move.flush_model()
        # Check Budget
        self.env["budget.period"].check_budget(doclines, doc_type=doc_type)
        # Remove commits
        for budget_move in budget_moves:
            budget_move.unlink()
        # Delete date commit from system create auto only
        doclines.filtered(
            lambda line, vals_date_commit=vals_date_commit: line.id in vals_date_commit
        ).write({"date_commit": False})
        # Remove uncommit budget
        if budget_moves_uncommit:
            budget_moves_uncommit.unlink()

    @api.model
    def check_over_returned_budget(self, docline, reverse=False):
        self = self.sudo()
        doc = docline[docline._doc_rel]
        budget_moves = doc[docline._budget_field()]
        credit = sum(budget_moves.mapped("credit"))
        debit = sum(budget_moves.mapped("debit"))
        amount_credit = debit if reverse else credit
        amount_debit = credit if reverse else debit
        # For now, when any over returned budget, make immediate adjustment
        if float_compare(amount_credit, amount_debit, 2) == 1:
            docline.with_context(
                use_amount_commit=True,
                commit_note=self.env._(
                    f"Over returned auto adjustment, {docline.display_name}"
                ),
                adj_commit=True,
            ).commit_budget(reverse=True)

    @api.model
    def _get_eligible_budget_period(self, date=False, doc_type=False):
        """
        Get the eligible budget period based on the specified date and document type.
        """
        if not date:
            date = fields.Date.context_today(self)
        BudgetPeriod = self.env["budget.period"]
        budget_period = BudgetPeriod.search(
            [("bm_date_from", "<=", date), ("bm_date_to", ">=", date)]
        )
        if budget_period and len(budget_period) > 1:
            raise ValidationError(
                self.env._(
                    f"Multiple Budget Periods found for date {date}.\nPlease ensure "
                    "there is only one Budget Period valid for this date."
                )
            )
        if not doc_type:
            return budget_period
        # Get period control budget.
        # if doctype is account, check special control too.
        if doc_type == "account":
            return budget_period.filtered(
                lambda bp: (bp.control_budget and bp.account)
                or (not bp.control_budget and bp.account)
            )
        # Other module control budget must hook it for filter
        return budget_period

    @api.model
    def _prepare_controls(self, budget_period, doclines):
        controls = set()
        control_analytics = budget_period.control_analytic_account_ids
        budget_moves = doclines.mapped(doclines._budget_field())
        # Get budget moves from the period only
        budget_moves_period = budget_moves.filtered(
            lambda move, budget_period=budget_period: move.date
            >= budget_period.bm_date_from
            and move.date <= budget_period.bm_date_to
        )
        budget_control_key = self.env.company.budget_control_key
        need_control = self.env.context.get("need_control")
        for budget_move in budget_moves_period:
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
    def _get_kpi_by_control_key(self, template_lines, control):
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
            raise UserError(
                self.env._(
                    f"Chosen {control_name} {control.display_name} is not valid "
                    "in template"
                )
            )
        raise UserError(
            self.env._(
                f"Template Lines has more than one KPI being "
                f"referenced by the same {control_name} {control.display_name}"
            )
        )

    def _get_where_domain(self, analytic_id, template_lines):
        """Return the WHERE clause for the budget monitoring query."""
        if (
            not template_lines
            or self.env.context.get("control_level", False) == "analytic"
        ):
            return f"analytic_account_id = {analytic_id}"
        kpi_domain = (
            f"= {template_lines.kpi_id.id}"
            if len(template_lines) == 1
            else f"in {tuple(template_lines.kpi_id.ids)}"
        )
        return f"analytic_account_id = {analytic_id} and kpi_id {kpi_domain}"

    def _get_budget_monitor_report(self):
        """Hook for add context"""
        return self.env["budget.monitor.report"]

    def _get_budget_avaiable(self, analytic_id, template_lines):
        self.env.flush_all()
        self.env.cr.execute(
            SQL(
                f"""
                    SELECT *
                    FROM (%s) report
                    WHERE {self._get_where_domain(analytic_id, template_lines)}
                """,
                SQL(self._get_budget_monitor_report()._table_query),
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
        company = self.env.user.company_id
        doc_currency = self.env.context.get("doc_currency")
        date_commit = self.env.context.get("date_commit")
        for control in controls:
            analytic_id = control["analytic_id"]
            # Get the KPI(s) to check the budget,
            # in case the control level is set to "analytic_kpi"
            if budget_period.control_level == "analytic_kpi":
                template_lines = self._get_filter_template_line(
                    all_template_lines, control
                )
            # Get the available budget for the specified analytic account and KPI(s)
            query_data = self.with_context(
                control_level=budget_period.control_level
            )._get_budget_avaiable(analytic_id, template_lines)
            # Check kpi not valid for budgeting when control level analytic & kpi
            data_budget = any(
                query["amount_type"] == "10_budget" for query in query_data
            )
            if budget_period.control_level == "analytic_kpi" and not data_budget:
                raise UserError(
                    _("Chosen KPI %s is not valid for budgeting")
                    % template_lines.display_name
                )
            balance = sum(
                q["amount"]
                for q in query_data
                if q["amount"] is not None and q["budget_period_id"] == budget_period.id
            )
            # Show a warning if the budget is not sufficient
            if float_compare(balance, 0.0, precision_rounding=2) == -1:
                # Convert the balance to the document currency
                balance_currency = self._get_balance_currency(
                    company, balance, doc_currency, date_commit
                )
                fomatted_balance = format_amount(
                    self.env, balance_currency, doc_currency
                )
                analytic_name = Analytic.browse(analytic_id).display_name
                if budget_period.control_level == "analytic_kpi":
                    analytic_name = f"{template_lines.display_name} & {analytic_name}"
                warnings.append(
                    _("{analytic_name}, will result in {formatted_balance}").format(
                        analytic_name=analytic_name, formatted_balance=fomatted_balance
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
        budget_info = {col: 0 for col in query["info_cols"].keys()}
        budget_info["amount_commit"] = 0
        for col, (amount_type, is_commit) in query["info_cols"].items():
            info = list(
                filter(
                    lambda dataset, amount_type=amount_type: dataset["amount_type"]
                    == amount_type,
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
            elif amount_type == "80_actual":  # Negate consumed
                budget_info[col] = -amount
            else:
                budget_info[col] = amount
        budget_info["amount_consumed"] = (
            budget_info["amount_commit"] + budget_info["amount_actual"]
        )
        budget_info["amount_balance"] = (
            budget_info["amount_budget"] - budget_info["amount_consumed"]
        )
        return budget_info

    def _budget_info_query(self):
        query = {
            "info_cols": {
                "amount_budget": (
                    "10_budget",
                    False,
                ),  # (amount_type, is_commit)
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
