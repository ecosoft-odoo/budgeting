# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"
    _rec_names_search = ["name", "code", "budget_period_id"]

    budget_period_id = fields.Many2one(
        comodel_name="budget.period",
    )
    budget_control_ids = fields.One2many(
        string="Budget Control(s)",
        comodel_name="budget.control",
        inverse_name="analytic_account_id",
        readonly=True,
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
    budget_company_ids = fields.Many2many(
        comodel_name="res.company",
        compute="_compute_budget_company",
        store=True,
        readonly=False,
        string="Allowed Budget Companies",
        help="Companies that this analytic account is allowed to use",
    )
    amount_budget = fields.Monetary(
        string="Budgeted",
        compute="_compute_amount_budget_info",
        help="Sum of amount plan",
    )
    amount_consumed = fields.Monetary(
        string="Consumed",
        compute="_compute_amount_budget_info",
        help="Consumed = Total Commitments + Actual",
    )
    amount_balance = fields.Monetary(
        string="Available",
        compute="_compute_amount_budget_info",
        help="Available = Total Budget - Consumed",
    )
    initial_available = fields.Monetary(
        copy=False,
        readonly=True,
        tracking=True,
        help="Initial Balance come from carry forward available accumulated",
    )
    initial_commit = fields.Monetary(
        string="Initial Commitment",
        copy=False,
        readonly=True,
        tracking=True,
        help="Initial Balance from carry forward commitment",
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

    @api.depends("budget_period_id")
    def _compute_bm_date(self):
        """Default effective date, but changable"""
        for rec in self:
            rec.bm_date_from = rec.budget_period_id.bm_date_from
            rec.bm_date_to = rec.budget_period_id.bm_date_to

    @api.depends("company_id")
    def _compute_budget_company(self):
        for rec in self:
            rec.budget_company_ids = rec.company_id

    @api.constrains("company_id", "budget_company_ids")
    def _check_budget_company(self):
        """
        If analytic account is in company,
        then it must be in Allowed Budget Companies only
        """
        for rec in self:
            if not rec.company_id:
                continue

            if rec.company_id and rec.company_id != rec.budget_company_ids:
                raise UserError(
                    self.env._(
                        "Analytic Account Company must be in Allowed Budget Companies"
                    )
                )

    def _filter_by_analytic_account(self, val):
        if val["analytic_account_id"][0] == self.id:
            return True
        return False

    def _compute_amount_budget_info(self):
        """Note: This method is similar to BCS._compute_budget_info"""
        BudgetPeriod = self.env["budget.period"]
        MonitorReport = self.env["budget.monitor.report"]
        query = BudgetPeriod._budget_info_query()
        analytic_ids = self.ids
        # Retrieve budgeting data for a list of budget_control
        domain = [("analytic_account_id", "in", analytic_ids)]
        # Optional filters by context
        ctx = self.env.context.copy()
        if ctx.get("no_fwd_commit"):
            domain.append(("fwd_commit", "=", False))
        if ctx.get("budget_period_ids"):
            domain.append(("budget_period_id", "in", ctx["budget_period_ids"]))
        # --
        admin_uid = self.env.ref("base.user_admin").id
        dataset_all = MonitorReport.with_user(admin_uid).read_group(
            domain=domain,
            fields=["analytic_account_id", "amount_type", "amount"],
            groupby=["analytic_account_id", "amount_type"],
            lazy=False,
        )
        for rec in self:
            # Filter according to budget_control parameter
            dataset = list(
                filter(
                    lambda dataset: rec._filter_by_analytic_account(dataset),
                    dataset_all,
                )
            )
            # Get data from dataset
            budget_info = BudgetPeriod.get_budget_info_from_dataset(query, dataset)
            rec.amount_budget = budget_info["amount_budget"]
            rec.amount_consumed = budget_info["amount_consumed"]
            rec.amount_balance = rec.amount_budget - rec.amount_consumed

    def _find_next_analytic(self, next_date_range):
        self.ensure_one()
        Analytic = self.env["account.analytic.account"]
        next_analytic = Analytic.search(
            [("name", "=", self.name), ("bm_date_from", "=", next_date_range)]
        )
        return next_analytic

    def _update_val_analytic(self, next_analytic, next_date_range):
        BudgetPeriod = self.env["budget.period"]
        vals_update = {}
        type_id = next_analytic.budget_period_id.plan_date_range_type_id
        period_id = BudgetPeriod.search(
            [
                ("bm_date_from", "=", next_date_range),
                ("plan_date_range_type_id", "=", type_id.id),
            ]
        )
        if period_id:
            vals_update = {"budget_period_id": period_id.id}
        else:
            # No budget period found, update date_from and date_to
            vals_update = {
                "bm_date_from": next_date_range,
                "bm_date_to": next_analytic.bm_date_to + relativedelta(years=1),
            }
        return vals_update

    def _auto_create_next_analytic(self, next_date_range):
        self.ensure_one()
        # Core odoo will add (copy) after name, but we need same name
        next_analytic = self.copy(default={"name": self.name})
        val_update = self._update_val_analytic(next_analytic, next_date_range)
        next_analytic.write(val_update)
        return next_analytic

    def next_year_analytic(self, auto_create=True):
        """Find next analytic from analytic date_to + 1,
        if bm_date_to = False, this is an open end analytic, always return False"""
        self.ensure_one()
        if not self.bm_date_to:
            return False
        next_date_range = self.bm_date_to + relativedelta(days=1)
        next_analytic = self._find_next_analytic(next_date_range)
        if not next_analytic and auto_create:
            next_analytic = self._auto_create_next_analytic(next_date_range)
        return next_analytic

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
                    f"{names}"
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
                    f"Following analytics have no budget control sheet:\n{names}"
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
                    f"Budget control sheets for the following analytics "
                    f"are not in control:\n{names}"
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

    def action_edit_initial_available(self):
        return {
            "name": self.env._("Edit Analytic Budget"),
            "type": "ir.actions.act_window",
            "res_model": "analytic.budget.edit",
            "view_mode": "form",
            "target": "new",
            "context": {"default_initial_available": self.initial_available},
        }
