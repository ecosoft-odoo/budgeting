# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class BudgetControl(models.Model):
    _name = "budget.control"
    _description = "Budget Control"
    _inherit = ["mail.thread"]
    _order = "budget_id desc, analytic_account_id"

    name = fields.Char(
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
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
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    budget_id = fields.Many2one(
        comodel_name="mis.budget",
        string="MIS Budget",
        required=True,
        ondelete="restrict",
        domain=lambda self: self._get_mis_budget_domain(),
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="List of mis.budget created by and linked to budget.period",
    )
    date_from = fields.Date(
        related="budget_id.date_from",
    )
    date_to = fields.Date(
        related="budget_id.date_to",
    )
    budget_period_id = fields.Many2one(
        comodel_name="budget.period",
        compute="_compute_budget_period_id",
        store=True,
        help="Budget Period that inline with date from/to",
    )
    active = fields.Boolean(
        default=True,
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        ondelete="restrict",
    )
    analytic_group = fields.Many2one(
        comodel_name="account.analytic.group",
        string="Analytic Group",
        related="analytic_account_id.group_id",
        store=True,
    )
    item_ids = fields.One2many(
        comodel_name="mis.budget.item",
        inverse_name="budget_control_id",
        string="Budget Items",
        copy=False,
        context={"active_test": False},
        readonly=True,
        states={
            "draft": [("readonly", False)],
            "submit": [("readonly", False)],
        },
    )
    plan_date_range_type_id = fields.Many2one(
        comodel_name="date.range.type",
        string="Plan Date Range",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    init_budget_commit = fields.Boolean(
        string="Initial Budget By Commitment",
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="If checked, the newly created budget control sheet will has "
        "initial budget equal to current budget commitment of its year.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency", related="company_id.currency_id"
    )
    allocated_amount = fields.Monetary(
        string="Allocated",
        help="Initial total amount for plan",
    )
    released_amount = fields.Monetary(
        string="Released",
        compute="_compute_allocated_released_amount",
        store=True,
        readonly=False,
        help="Total amount for transfer current",
    )
    # Total Amount
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
        help="Total Commit = Sum of PR / PO / EX / AV commit",
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
    mis_report_id = fields.Many2one(
        comodel_name="mis.report",
        related="budget_period_id.report_id",
        readonly=True,
    )
    use_all_kpis = fields.Boolean(string="Use All KPIs")
    kpi_ids = fields.Many2many(
        string="KPIs",
        comodel_name="mis.report.kpi",
        relation="kpi_budget_contol_rel",
        column1="budget_control_id",
        column2="kpi_id",
        domain="[('report_id', '=', mis_report_id), ('budgetable', '=', True)]",
        readonly=True,
        states={"draft": [("readonly", False)]},
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
    # _sql_constraints = [
    #     ("name_uniq", "UNIQUE(name)", "Name must be unique!"),
    #     (
    #         "budget_control_uniq",
    #         "UNIQUE(budget_id, analytic_account_id)",
    #         "Duplicated analytic account for the same budget!",
    #     ),
    # ]

    @api.onchange("use_all_kpis")
    def _onchange_use_all_kpis(self):
        if self.use_all_kpis:
            domain = [
                ("report_id", "=", self.mis_report_id.id),
                ("budgetable", "=", True),
            ]
            self.kpi_ids = self.env["mis.report.kpi"].search(domain)
        else:
            self.kpi_ids = False

    def action_confirm_state(self):
        return {
            "name": _("Confirmation"),
            "type": "ir.actions.act_window",
            "res_model": "budget.state.confirmation",
            "view_mode": "form",
            "target": "new",
            "context": self._context,
        }

    @api.depends("date_from", "date_to")
    def _compute_budget_period_id(self):
        Period = self.env["budget.period"]
        for rec in self:
            period = Period.search(
                [
                    ("bm_date_from", "=", rec.date_from),
                    ("bm_date_to", "=", rec.date_to),
                ]
            )
            rec.budget_period_id = period[:1]

    @api.depends("allocated_amount")
    def _compute_allocated_released_amount(self):
        for rec in self:
            rec.released_amount = rec.allocated_amount

    def _compute_budget_info(self):
        BudgetPeriod = self.env["budget.period"]
        for rec in self:
            budget_period = BudgetPeriod.search(
                [("mis_budget_id", "=", rec.budget_id.id)]
            )
            analytic_ids = [rec.analytic_account_id.id]
            info = budget_period.get_budget_info(analytic_ids)
            for key, value in info.items():
                rec[key] = value
            rec.amount_consumed = rec.amount_commit + rec.amount_actual

    @api.model
    def _get_mis_budget_domain(self):
        all_budget_periods = self.env["budget.period"].search([])
        return [("id", "in", all_budget_periods.mapped("mis_budget_id").ids)]

    def get_report_amount(self, kpi_names=None, col_names=None):
        self.ensure_one()
        BudgetPeriod = self.env["budget.period"]
        budget_period = BudgetPeriod.search(
            [("mis_budget_id", "=", self.budget_id.id)]
        )
        budget_period.ensure_one()
        return budget_period._get_amount(
            budget_period.report_instance_id.id,
            kpi_names=kpi_names,
            col_names=col_names,
            analytic_id=self.analytic_account_id.id,
        )

    def do_init_budget_commit(self, init):
        """Initialize budget with current commitment amount."""
        for plan in self:
            plan.update({"init_budget_commit": init})
            if not init or not plan.init_budget_commit or not plan.item_ids:
                continue
            init_date = min(plan.item_ids.mapped("date_from"))
            init_items = plan.item_ids.filtered(
                lambda l: l.date_from == init_date
            )
            for item in init_items:
                kpi_name = item.kpi_expression_id.kpi_id.name
                balance = plan.get_report_amount(
                    kpi_names=[kpi_name], col_names=["Available"]
                )
                item.update({"amount": -balance})

    @api.onchange("init_budget_commit")
    def _onchange_init_budget_commit(self):
        self.do_init_budget_commit(self.init_budget_commit)

    def _compare_plan_fund(self, plan_amount, fund_amount):
        """ Check total amount plan have to equal released amount """
        amount_compare = (
            float_compare(
                plan_amount,
                fund_amount,
                precision_rounding=self.currency_id.rounding,
            )
            != 0
        )
        message = _(
            "Planning amount should equal to the released amount {:,.2f} {}".format(
                fund_amount, self.currency_id.symbol
            )
        )
        return amount_compare, message

    def action_draft(self):
        self.write({"state": "draft"})

    def action_submit(self):
        self.write({"state": "submit"})

    def action_done(self):
        for rec in self:
            plan_amount = rec.amount_budget
            fund_amount = rec.released_amount
            amount_compare, message = rec._compare_plan_fund(
                plan_amount, fund_amount
            )
            if amount_compare:
                raise UserError(message)
        self.write({"state": "done"})

    def action_cancel(self):
        self.write({"state": "cancel"})

    def _domain_kpi_expression(self):
        return [
            ("kpi_id.report_id", "=", self.budget_id.report_id.id),
            ("kpi_id.budgetable", "=", True),
            ("kpi_id.id", "in", self.kpi_ids.ids),
        ]

    def _get_value_items(self, date_range, kpi_expression):
        self.ensure_one()
        items = [
            {
                "budget_id": self.budget_id.id,
                "kpi_expression_id": kpi_expression.id,
                "date_range_id": date_range.id,
                "date_from": date_range.date_start,
                "date_to": date_range.date_end,
                "analytic_account_id": self.analytic_account_id.id,
            }
        ]
        return items

    def prepare_budget_control_matrix(self):
        KpiExpression = self.env["mis.report.kpi.expression"]
        DateRange = self.env["date.range"]
        for plan in self:
            if not self._context.get("skip_unlink", False):
                plan.item_ids.unlink()
            if not plan.plan_date_range_type_id:
                raise UserError(_("Please select range"))
            domain_kpi = plan._domain_kpi_expression()
            date_ranges = DateRange.search(
                [
                    ("type_id", "=", plan.plan_date_range_type_id.id),
                    ("date_start", ">=", plan.date_from),
                    ("date_end", "<=", plan.date_to),
                ]
            )
            kpi_expressions = KpiExpression.search(domain_kpi)
            items = []
            for date_range in date_ranges:
                for kpi_expression in kpi_expressions:
                    vals = plan._get_value_items(date_range, kpi_expression)
                    items += vals
            plan.write({"item_ids": [(0, 0, val) for val in items]})
            # Also reset the carry over budget
            plan.init_budget_commit = False

    def _report_instance(self):
        self.ensure_one()
        budget_period = self.env["budget.period"].search(
            [("mis_budget_id", "=", self.budget_id.id)]
        )
        ctx = {"filter_analytic_ids": [self.analytic_account_id.id]}
        return budget_period.report_instance_id.with_context(ctx)

    def preview(self):
        return self._report_instance().preview()

    def print_pdf(self):
        return self._report_instance().print_pdf()

    def export_xls(self):
        return self._report_instance().export_xls()
