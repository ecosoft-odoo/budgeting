# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command


class SaleOrder(models.Model):
    _inherit = "sale.order"

    budget_control_id = fields.Many2one(
        comodel_name="budget.control",
        index=True,
        copy=False,
    )
    can_create_budget = fields.Boolean(
        compute="_compute_can_create_budget",
    )
    generated_project_budget_scope = fields.Selection(
        selection=[
            ("lifetime", "Lifetime"),
            ("fiscal", "Fiscal Period"),
        ],
        string="Project Budget Scope",
        required=True,
        default="lifetime",
        help="Applied only when confirmation creates a new Project. Lifetime "
        "controls the total estimated cost with one budget; Fiscal "
        "Period creates annual Budget Controls.",
    )
    will_create_project = fields.Boolean(
        compute="_compute_will_create_project",
    )

    @api.depends("budget_control_id")
    def _compute_can_create_budget(self):
        for order in self:
            order.can_create_budget = not order.budget_control_id

    @api.depends("order_line.product_id.service_tracking")
    def _compute_will_create_project(self):
        for order in self:
            order.will_create_project = any(
                tracking in ("project_only", "task_in_project")
                for tracking in order.order_line.mapped("product_id.service_tracking")
            )

    def action_confirm(self):
        """Bypass stock budget commit check during SO confirmation.

        When SO is confirmed, the system auto-creates a Delivery Order (DO).
        Budget Control may not yet be confirmed at this point (user needs to
        set KPIs first). The bypass context prevents the budget check from
        failing during DO creation. Subsequent DO operations (validate, etc.)
        will enforce the budget check normally, forcing the user to confirm
        the Budget Control before proceeding.
        """
        return super(
            SaleOrder, self.with_context(force_no_budget_check=True)
        ).action_confirm()

    def action_create_budget_control(self):
        """Manual create budget control"""
        self.ensure_one()
        if not self._get_budget_project() and self.will_create_project:
            raise UserError(
                self.env._(
                    "Confirm the Sale Order first so Odoo can create its Project "
                    "before creating the Budget Control."
                )
            )
        self._create_budget_control()
        return True

    def _action_confirm(self):
        projects_before = {order.id: order._get_budget_project() for order in self}
        res = super()._action_confirm()
        for order in self:
            project = order._get_budget_project()
            generated_from_order = (
                project
                and not projects_before[order.id]
                and project.sale_line_id.order_id == order
            )
            if generated_from_order:
                project.budget_control_scope = order.generated_project_budget_scope
        self.filtered(
            lambda rec: not rec.budget_control_id and rec._get_budget_project()
        )._create_budget_control()
        return res

    def _get_budget_project(self):
        self.ensure_one()
        projects = self.project_id | self.order_line.project_id
        if len(projects) > 1:
            raise UserError(
                self.env._(
                    "Sale Order %(order)s has more than one Project. Split it into "
                    "one Sale Order per budgeted Project.",
                    order=self.display_name,
                )
            )
        return projects

    def _get_sale_budget_period(self, analytic_account):
        self.ensure_one()
        date = self.date_order.date() if self.date_order else fields.Date.today()
        budget_period = (
            self.env["budget.period"]
            .with_company(self.company_id)
            ._get_eligible_budget_period(date)
        )
        if not budget_period:
            raise UserError(
                self.env._(
                    "No budget period found for date %(date)s on sale order "
                    "%(order)s.",
                    date=date,
                    order=self.name,
                )
            )
        project = self._get_budget_project()
        if (
            project
            and analytic_account == project.account_id
            and project.budget_control_scope == "lifetime"
        ):
            return project._ensure_lifetime_budget_period(budget_period, date)
        return budget_period

    def _create_budget_control(self):
        BudgetControl = self.env["budget.control"]
        for order in self:
            analytic_account = order._get_budget_analytic_account()
            if not analytic_account:
                continue

            budget_period = order._get_sale_budget_period(analytic_account)
            existing = BudgetControl.search(
                [
                    ("analytic_account_id", "=", analytic_account.id),
                    ("budget_period_id", "=", budget_period.id),
                    ("active", "=", True),
                    ("state", "!=", "cancel"),
                ],
                limit=1,
            )
            if existing:
                # New SO on the same analytic and period adds to the existing
                # control. Reconfirming the same SO must not add it twice.
                if order not in existing.sale_order_ids:
                    vals = {"sale_order_ids": [Command.link(order.id)]}
                    if not existing.budget_plan_id:
                        if existing.state != "draft":
                            raise UserError(
                                self.env._(
                                    "Budget Control %(control)s must be set to Draft "
                                    "before adding another Sale Order.",
                                    control=existing.display_name,
                                )
                            )
                        add_amount = order._get_budget_control_allocated_amount()
                        vals["allocated_amount"] = (
                            existing.allocated_amount + add_amount
                        )
                    existing.write(vals)
                order.budget_control_id = existing.id
            else:
                vals = order._prepare_budget_control_vals(
                    analytic_account, budget_period
                )
                budget_control = BudgetControl.create(vals)
                order.budget_control_id = budget_control.id
            order._update_order_lines_analytic(analytic_account)

    def _get_budget_analytic_account(self):
        """Return the analytic account to use for budget control.

        By default, use the project's analytic account. If there is no
        Project, create an analytic account using the configured Sale Budget
        Analytic Plan.
        """
        self.ensure_one()
        project = self._get_budget_project()
        if project:
            if not project.account_id:
                raise UserError(
                    self.env._(
                        "Project %(project)s needs an analytic account before a "
                        "Budget Control can be created.",
                        project=project.display_name,
                    )
                )
            return project.account_id
        plan = self.company_id.budget_sale_analytic_plan_id
        if not plan:
            raise UserError(
                self.env._(
                    "Please configure 'Sale Budget Analytic Plan' in Settings > "
                    "Budgeting > Budget Control Options before creating budget from "
                    "a sale order without project."
                )
            )
        return self.env["account.analytic.account"].create(
            {"name": self.name, "plan_id": plan.id}
        )

    def _prepare_budget_control_vals(self, analytic_account, budget_period):
        self.ensure_one()
        return {
            "name": analytic_account.name,
            "analytic_account_id": analytic_account.id,
            "budget_period_id": budget_period.id,
            "plan_date_range_type_id": budget_period.plan_date_range_type_id.id,
            "currency_id": self.company_id.currency_id.id,
            "allocated_amount": self._get_budget_control_allocated_amount(),
            "sale_order_ids": [Command.link(self.id)],
        }

    def _get_budget_control_allocated_amount(self):
        """Return the SO cost allocated to a budget control in company currency.

        Keep the default implementation based on ``purchase_price`` so this
        addon remains independent from optional sale cost customizations.
        Implementations that use another cost source can override this hook.
        """
        self.ensure_one()
        amount = sum(
            line.purchase_price * line.product_uom_qty for line in self.order_line
        )
        return self._convert_budget_amount_to_company_currency(amount)

    def _get_budget_control_sale_amount(self):
        """Return the untaxed SO amount in company currency."""
        self.ensure_one()
        return self._convert_budget_amount_to_company_currency(self.amount_untaxed)

    def _convert_budget_amount_to_company_currency(self, amount):
        """Convert an amount expressed in SO currency to company currency.

        Optional addons can override ``_get_budget_control_currency_rate`` to
        provide another rate source, such as a manual currency rate on the SO.
        """
        self.ensure_one()
        company = self.company_id or self.env.company
        rate = self._get_budget_control_currency_rate()
        return company.currency_id.round(amount * rate)

    def _get_budget_control_currency_rate(self):
        """Return the SO-to-company currency multiplier used by the budget.

        This hook intentionally belongs to ``sale.order`` so an optional addon
        can use SO-specific information. For example, a manual currency addon
        can override this method, return its manual rate when enabled, and call
        ``super()`` otherwise.
        """
        self.ensure_one()
        company = self.company_id or self.env.company
        currency = self.currency_id or company.currency_id
        conversion_date = self.date_order or fields.Date.context_today(self)
        return self.env["res.currency"]._get_conversion_rate(
            currency,
            company.currency_id,
            company,
            conversion_date,
        )

    def action_open_budget_control(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "budget.control",
            "view_mode": "form",
            "res_id": self.budget_control_id.id,
        }

    def _update_order_lines_analytic(self, analytic_account):
        """Add the budget analytic without replacing other analytic plans."""
        self.ensure_one()
        for line in self.order_line.filtered(lambda rec: not rec.display_type):
            distribution = line.analytic_distribution or {}
            account_ids = {
                int(account_id) for key in distribution for account_id in key.split(",")
            }
            applied_accounts = (
                self.env["account.analytic.account"].browse(account_ids).exists()
            )
            if analytic_account in applied_accounts:
                continue
            if analytic_account.root_plan_id in applied_accounts.root_plan_id:
                raise UserError(
                    self.env._(
                        "Sale order line %(line)s already uses another analytic "
                        "account from plan %(plan)s.",
                        line=line.display_name,
                        plan=analytic_account.root_plan_id.display_name,
                    )
                )
            line.analytic_distribution = (
                {
                    f"{key},{analytic_account.id}": percentage
                    for key, percentage in distribution.items()
                }
                if distribution
                else {str(analytic_account.id): 100.0}
            )
