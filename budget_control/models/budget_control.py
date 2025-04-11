# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class BudgetControl(models.Model):
    _name = "budget.control"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Budget Control"
    _order = "analytic_account_id"

    name = fields.Char(
        required=True,
        tracking=True,
    )
    assignee_id = fields.Many2one(
        comodel_name="res.users",
        string="Assigned To",
        domain=lambda self: [
            (
                "groups_id",
                "in",
                [self.env.ref("budget_control.group_budget_control_user").id],
            )
        ],
        tracking=True,
        copy=False,
    )
    budget_period_id = fields.Many2one(
        comodel_name="budget.period",
        help="Budget Period that inline with date from/to",
        ondelete="restrict",
    )
    date_from = fields.Date(related="budget_period_id.bm_date_from")
    date_to = fields.Date(related="budget_period_id.bm_date_to")
    active = fields.Boolean(default=True)
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        required=True,
        tracking=True,
        ondelete="restrict",
    )
    analytic_plan = fields.Many2one(
        comodel_name="account.analytic.plan",
        related="analytic_account_id.plan_id",
        store=True,
    )
    line_ids = fields.One2many(
        comodel_name="budget.control.line",
        inverse_name="budget_control_id",
        string="Budget Lines",
        copy=True,
        context={"active_test": False},
    )
    plan_date_range_type_id = fields.Many2one(
        comodel_name="date.range.type",
        string="Plan Date Range",
        required=True,
    )
    init_budget_commit = fields.Boolean(
        string="Initial Budget By Commitment",
        help="If checked, the newly created budget control sheet will has "
        "initial budget equal to current budget commitment of its year.",
    )
    company_ids = fields.Many2many(
        comodel_name="res.company",
        related="analytic_account_id.budget_company_ids",
        relation="budget_control_company_rel",
        column1="budget_control_id",
        column2="company_id",
        store=True,
        string="Companies",
        tracking=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        required=True,
        tracking=True,
    )
    allocated_amount = fields.Monetary(
        string="Allocated",
        help="Initial total amount for plan",
        tracking=True,
    )
    released_amount = fields.Monetary(
        string="Released",
        compute="_compute_allocated_released_amount",
        store=True,
        tracking=True,
        help="Total amount for transfer current",
    )
    diff_amount = fields.Monetary(
        compute="_compute_diff_amount",
        help="Diff from Released - Budget",
    )
    # Total Amount
    amount_initial = fields.Monetary(
        string="Initial Balance",
        compute="_compute_initial_balance",
    )
    amount_budget = fields.Monetary(
        string="Budget",
        compute="_compute_budget_info",
        help="Sum of amount plan",
    )
    amount_actual = fields.Monetary(
        string="Actual",
        compute="_compute_budget_info",
        help="Sum of actual amount",
    )
    amount_commit = fields.Monetary(
        string="Commit",
        compute="_compute_budget_info",
        help="Total Commit = Sum of PR / PO / EX / AV commit (extension module)",
    )
    amount_consumed = fields.Monetary(
        string="Consumed",
        compute="_compute_budget_info",
        help="Consumed = Total Commitments + Actual",
    )
    amount_balance = fields.Monetary(
        string="Available",
        compute="_compute_budget_info",
        help="Available = Total Budget - Consumed",
    )
    template_id = fields.Many2one(
        comodel_name="budget.template",
        related="budget_period_id.template_id",
        readonly=True,
    )
    use_all_kpis = fields.Boolean(
        string="Use All KPIs",
    )
    template_line_ids = fields.Many2many(
        string="KPIs",  # Template line = 1 KPI, name for users
        comodel_name="budget.template.line",
        relation="budget_template_line_budget_contol_rel",
        column1="budget_control_id",
        column2="template_line_id",
        compute="_compute_template_line_ids",
        store=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submit", "Submitted"),
            ("done", "Controlled"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        readonly=True,
        copy=False,
        index=True,
        default="draft",
        tracking=True,
    )
    transfer_item_ids = fields.Many2many(
        comodel_name="budget.transfer.item",
        string="Transfers",
        compute="_compute_transfer_item_ids",
    )
    transferred_amount = fields.Monetary(
        compute="_compute_transferred_amount",
    )

    @api.constrains("active", "state", "analytic_account_id", "budget_period_id")
    def _check_budget_control_unique(self):
        """Not allow multiple active budget control on same period"""
        analytic_ids = self.mapped("analytic_account_id").ids
        period_ids = self.mapped("budget_period_id").ids
        if not analytic_ids or not period_ids:
            return  # Nothing to check if no data

        query = """
            SELECT analytic_account_id, budget_period_id, COUNT(*)
            FROM budget_control
            WHERE active = TRUE AND state != 'cancel'
                AND analytic_account_id IN %s
                AND budget_period_id IN %s
            GROUP BY analytic_account_id, budget_period_id
            HAVING COUNT(*) > 1
        """
        params = (tuple(analytic_ids), tuple(period_ids))

        self.env.cr.execute(query, params)
        res = self.env.cr.dictfetchall()
        if not res:
            return  # No duplicates found

        analytic_ids = [x["analytic_account_id"] for x in res]
        analytics = self.env["account.analytic.account"].browse(analytic_ids)
        raise UserError(
            self.env._(
                f"Multiple budget control on the same period for: "
                f"{', '.join(analytics.mapped('name'))}"
            )
        )

    @api.depends("analytic_account_id")
    def _compute_initial_balance(self):
        for rec in self:
            rec.amount_initial = (
                rec.analytic_account_id.initial_available
                + rec.analytic_account_id.initial_commit
            )

    @api.constrains("line_ids")
    def _check_budget_control_over_consumed(self):
        BudgetPeriod = self.env["budget.period"]
        if self.env.context.get("edit_amount", False):
            return

        for rec in self.filtered(
            lambda control: control.budget_period_id.control_level == "analytic_kpi"
        ):
            for line in rec.line_ids:
                # Filter according to budget_control parameter
                query, dataset_all = rec.with_context(
                    filter_kpi_ids=[line.kpi_id.id]
                )._get_query_dataset_all()
                # Get data from dataset
                budget_info = BudgetPeriod.get_budget_info_from_dataset(
                    query, dataset_all
                )
                if budget_info["amount_balance"] < 0:
                    raise UserError(
                        self.env._(
                            f"Total amount in KPI {line.name} will result in "
                            f"{budget_info['amount_balance']:,.2f}"
                        )
                    )

    @api.depends("use_all_kpis")
    def _compute_template_line_ids(self):
        for rec in self:
            rec.template_line_ids = False
            if rec.use_all_kpis:
                rec.template_line_ids = rec.template_id.line_ids

    def action_confirm_state(self):
        return {
            "name": self.env._("Confirmation"),
            "type": "ir.actions.act_window",
            "res_model": "budget.state.confirmation",
            "view_mode": "form",
            "target": "new",
            "context": self._context,
        }

    @api.depends("allocated_amount")
    def _compute_allocated_released_amount(self):
        for rec in self:
            rec.released_amount = rec.allocated_amount + rec.transferred_amount

    @api.depends("released_amount", "amount_budget")
    def _compute_diff_amount(self):
        for rec in self:
            rec.diff_amount = rec.released_amount - rec.amount_budget

    def _filter_by_budget_control(self, val):
        return (
            val["analytic_account_id"][0] == self.analytic_account_id.id
            and val["budget_period_id"][0] == self.budget_period_id.id
        )

    def _get_domain_dataset_all(self):
        """Retrieve budgeting data for a list of budget_control"""
        analytic_ids = self.mapped("analytic_account_id").ids
        budget_period_ids = self.mapped("budget_period_id").ids
        domain = [
            ("analytic_account_id", "in", analytic_ids),
            ("budget_period_id", "in", budget_period_ids),
        ]
        # Optional filters by context
        if self.env.context.get("no_fwd_commit"):
            domain.append(("fwd_commit", "=", False))
        if self.env.context.get("filter_kpi_ids"):
            domain.append(("kpi_id", "in", self.env.context.get("filter_kpi_ids")))
        return domain

    def _get_context_monitoring(self):
        """Support for add context in monitoring"""
        return self.env.context.copy()

    def _get_query_dataset_all(self):
        # Refresh data up to date
        self.env.flush_all()

        BudgetPeriod = self.env["budget.period"]
        MonitorReport = self.env["budget.monitor.report"]
        ctx = self._get_context_monitoring()
        query = BudgetPeriod._budget_info_query()
        domain = self._get_domain_dataset_all()
        dataset_all = MonitorReport.with_context(**ctx).read_group(
            domain=domain,
            fields=query["fields"],
            groupby=query["groupby"],
            lazy=False,
        )
        return query, dataset_all

    @api.depends("line_ids.amount")
    def _compute_budget_info(self):
        BudgetPeriod = self.env["budget.period"]
        query, dataset_all = self._get_query_dataset_all()
        for rec in self:
            # Filter according to budget_control parameter
            dataset = [x for x in dataset_all if rec._filter_by_budget_control(x)]
            # Get data from dataset
            budget_info = BudgetPeriod.get_budget_info_from_dataset(query, dataset)
            rec.update(budget_info)

    def _get_lines_init_date(self):
        self.ensure_one()
        init_date = min(self.line_ids.mapped("date_from"))
        return self.line_ids.filtered(
            lambda line, init_date=init_date: line.date_from == init_date
        )

    def do_init_budget_commit(self, init):
        """Initialize budget with current commitment amount."""
        for bc in self:
            bc.update({"init_budget_commit": init})
            if not init or not bc.init_budget_commit or not bc.line_ids:
                continue
            min(bc.line_ids.mapped("date_from"))
            lines = bc._get_lines_init_date()
            for line in lines:
                query_data = bc.budget_period_id._get_budget_avaiable(
                    bc.analytic_account_id.id, line.template_line_id
                )
                # Get init commit amount only
                balance_commit = sum(
                    q["amount"]
                    for q in query_data
                    if q["amount"] is not None
                    and q["amount_type"] not in ["10_budget", "80_actual"]
                )
                line.update({"amount": abs(balance_commit)})

    @api.onchange("init_budget_commit")
    def _onchange_init_budget_commit(self):
        self.do_init_budget_commit(self.init_budget_commit)

    def _check_budget_amount(self):
        for rec in self:
            # Check plan vs released
            if (
                float_compare(
                    rec.amount_budget,
                    rec.released_amount,
                    precision_rounding=rec.currency_id.rounding,
                )
                != 0
            ):
                raise UserError(
                    self.env._(
                        "Planning amount should equal to the "
                        "released amount {amount:,.2f} {symbol}"
                    ).format(amount=rec.released_amount, symbol=rec.currency_id.symbol)
                )
            # Check plan vs intial
            if (
                float_compare(
                    rec.amount_initial,
                    rec.amount_budget,
                    precision_rounding=rec.currency_id.rounding,
                )
                == 1
            ):
                raise UserError(
                    self.env._(
                        "Planning amount should be greater than "
                        "initial balance {amount:,.2f} {symbol}"
                    ).format(amount=rec.amount_initial, symbol=rec.currency_id.symbol)
                )

    def action_draft(self):
        return self.write({"state": "draft"})

    def action_submit(self):
        self._check_budget_amount()
        return self.write({"state": "submit"})

    def action_done(self):
        self._check_budget_amount()
        return self.write({"state": "done"})

    def action_cancel(self):
        return self.write({"state": "cancel"})

    def _domain_template_line(self):
        return [("id", "in", self.template_line_ids.ids)]

    def _get_dict_budget_lines(self, date_range, template_line):
        return {
            "template_line_id": template_line.id,
            "date_range_id": date_range.id,
            "date_from": date_range.date_start,
            "date_to": date_range.date_end,
            "analytic_account_id": self.analytic_account_id.id,
            "budget_control_id": self.id,
        }

    def _get_budget_lines(self, date_range, template_line):
        self.ensure_one()
        dict_value = self._get_dict_budget_lines(date_range, template_line)
        if self._context.get("keep_item_amount", False):
            # convert dict to list
            domain_item = [(k, "=", v) for k, v in dict_value.items()]
            line_amount = self.line_ids.search_read(
                domain=domain_item, fields=["amount"], limit=1
            )
            if line_amount:
                dict_value["amount"] = line_amount[0].get("amount", 0.0)
        return dict_value

    def prepare_budget_control_matrix(self):
        BudgetTemplateLine = self.env["budget.template.line"]
        DateRange = self.env["date.range"]
        for bc in self:
            if not bc.plan_date_range_type_id:
                raise UserError(self.env._("Please select range"))

            template_lines = BudgetTemplateLine.search(bc._domain_template_line())
            date_ranges = DateRange.search(
                [
                    ("type_id", "=", bc.plan_date_range_type_id.id),
                    ("date_start", ">=", bc.date_from),
                    ("date_end", "<=", bc.date_to),
                ]
            )
            items = [
                bc._get_budget_lines(date_range, template_line)
                for date_range in date_ranges  # Loop1
                for template_line in template_lines  # Loop2
            ]

        # Delete the existing budget lines
        self.mapped("line_ids").unlink()

        # Create the new budget lines and Reset the carry over budget
        self.write({"init_budget_commit": False})
        self.env["budget.control.line"].create(items)

    def _get_domain_budget_monitoring(self):
        return [("analytic_account_id", "=", self.analytic_account_id.id)]

    def _get_context_budget_monitoring(self):
        ctx = {"search_default_group_by_analytic_account": 1}
        return ctx

    def action_view_monitoring(self):
        self.ensure_one()
        ctx = self._get_context_budget_monitoring()
        domain = self._get_domain_budget_monitoring()
        return {
            "name": self.env._("Budget Monitoring"),
            "res_model": "budget.monitor.report",
            "view_mode": "pivot,list,graph",
            "domain": domain,
            "context": ctx,
            "type": "ir.actions.act_window",
        }

    def _get_domain_transfer_item_ids(self):
        self.ensure_one()
        return [
            ("state", "=", "transfer"),
            "|",
            ("budget_control_from_id", "=", self.id),
            ("budget_control_to_id", "=", self.id),
        ]

    def _compute_transfer_item_ids(self):
        TransferItem = self.env["budget.transfer.item"]
        for rec in self:
            items = TransferItem.search(rec._get_domain_transfer_item_ids())
            rec.transfer_item_ids = items

    @api.depends("transfer_item_ids")
    def _compute_transferred_amount(self):
        result = defaultdict(float)
        all_control_ids = self.ids
        # Fetch only necessary fields instead of full records
        transfer_items = self.env["budget.transfer.item"].search_read(
            domain=[
                ("state", "=", "transfer"),
                "|",
                ("budget_control_from_id", "in", all_control_ids),
                ("budget_control_to_id", "in", all_control_ids),
            ],
            fields=["budget_control_from_id", "budget_control_to_id", "amount"],
        )

        # Process all transfers in one loop
        for item in transfer_items:
            amount = item.get("amount", 0.0)
            result[item.get("budget_control_to_id")[0]] += amount
            result[item.get("budget_control_from_id")[0]] -= amount

        # Update computed fields
        for rec in self:
            rec.transferred_amount = result[rec.id]  # Will be 0.0 if not found

    def action_open_budget_transfer_item(self):
        self.ensure_one()
        ctx = self.env.context.copy()
        ctx.update({"create": False, "edit": False, "show_transfer": 1})
        return {
            "name": self.env._("Budget Transfer Items"),
            "type": "ir.actions.act_window",
            "res_model": "budget.transfer.item",
            "view_mode": "list,form",
            "context": ctx,
            "domain": [("id", "in", self.transfer_item_ids.ids)],
        }


class BudgetControlLine(models.Model):
    _name = "budget.control.line"
    _description = "Budget Control Lines"
    _order = "date_range_id, kpi_id"

    budget_control_id = fields.Many2one(
        comodel_name="budget.control",
        ondelete="cascade",
        index=True,
        required=True,
    )
    date_range_id = fields.Many2one(
        comodel_name="date.range",
    )
    date_from = fields.Date(required=True, string="From")
    date_to = fields.Date(required=True, string="To")
    analytic_account_id = fields.Many2one(comodel_name="account.analytic.account")
    amount = fields.Float(
        digits="Budget Precision",
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
    active = fields.Boolean(
        compute="_compute_active",
        readonly=True,
        store=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="budget_control_id.currency_id",
        index=True,
    )
    state = fields.Selection(related="budget_control_id.state", store=True)

    @api.depends("budget_control_id.active")
    def _compute_active(self):
        for rec in self:
            rec.active = rec.budget_control_id.active if rec.budget_control_id else True
