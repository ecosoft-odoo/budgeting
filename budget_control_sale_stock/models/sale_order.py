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

    @api.depends("budget_control_id", "project_id")
    def _compute_can_create_budget(self):
        for order in self:
            order.can_create_budget = not order.budget_control_id

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
        self._create_budget_control()
        return True

    def _action_confirm(self):
        res = super()._action_confirm()
        self.filtered(
            lambda rec: not rec.budget_control_id and rec.project_id
        )._create_budget_control()
        return res

    def _create_budget_control(self):
        BudgetPeriod = self.env["budget.period"]
        BudgetControl = self.env["budget.control"]
        for order in self:
            analytic_account = order._get_budget_analytic_account()
            if not analytic_account:
                continue

            date = order.date_order.date() if order.date_order else fields.Date.today()
            budget_period = BudgetPeriod.search(
                [("bm_date_from", "<=", date), ("bm_date_to", ">=", date)],
                limit=1,
            )
            if not budget_period:
                raise UserError(
                    self.env._(
                        f"No budget period found for date {date} "
                        f"on sale order {order.name}."
                    )
                )
            existing = BudgetControl.search(
                [
                    ("analytic_account_id", "=", analytic_account.id),
                    ("budget_period_id", "=", budget_period.id),
                    ("state", "!=", "cancel"),
                ],
                limit=1,
            )
            if existing:
                # New SO on same analytic+period: add to existing budget.
                # Same SO re-confirmed (reset to draft): skip to avoid
                # doubling the allocated amount.
                if order not in existing.sale_order_ids:
                    add_amount = sum(
                        line.purchase_price * line.product_uom_qty
                        for line in order.order_line
                    )
                    existing.write(
                        {
                            "allocated_amount": existing.allocated_amount + add_amount,
                            "sale_order_ids": [Command.link(order.id)],
                        }
                    )
                    existing.action_draft()
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

        By default, use the project's analytic account.
        If no project, auto-create an analytic account named after the sale order
        using the configured analytic plan from company settings.
        """
        self.ensure_one()
        project = self.project_id
        if project:
            return project.account_id
        plan = self.company_id.budget_sale_analytic_plan_id
        if not plan:
            raise UserError(
                self.env._(
                    "Please configure 'Sale Budget Analytic Plan' in Settings > "
                    "Invoicing > Budget Control before creating budget from "
                    "sale order without project."
                )
            )
        return self.env["account.analytic.account"].create(
            {"name": self.name, "plan_id": plan.id}
        )

    def _prepare_budget_control_vals(self, analytic_account, budget_period):
        self.ensure_one()
        allocated_amount = sum(
            line.purchase_price * line.product_uom_qty for line in self.order_line
        )
        return {
            "name": analytic_account.name,
            "analytic_account_id": analytic_account.id,
            "budget_period_id": budget_period.id,
            "plan_date_range_type_id": budget_period.plan_date_range_type_id.id,
            "currency_id": self.company_id.currency_id.id,
            "allocated_amount": allocated_amount,
            "sale_order_ids": [Command.link(self.id)],
        }

    def action_open_budget_control(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "budget.control",
            "view_mode": "form",
            "res_id": self.budget_control_id.id,
        }

    def _update_order_lines_analytic(self, analytic_account):
        """Update order lines analytic distribution with the given analytic account."""
        self.ensure_one()
        self.order_line.write(
            {"analytic_distribution": {str(analytic_account.id): 100.0}}
        )
