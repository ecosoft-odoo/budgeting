# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError


class BudgetLifetimeSetup(models.TransientModel):
    _name = "budget.lifetime.setup"
    _description = "Create Lifetime Budget"

    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        required=True,
        readonly=True,
    )
    name = fields.Char(required=True)
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    template_id = fields.Many2one(
        comodel_name="budget.template",
        required=True,
    )
    plan_date_range_type_id = fields.Many2one(
        comodel_name="date.range.type",
        string="Plan Date Range",
        required=True,
    )
    control_level = fields.Selection(
        selection=[
            ("analytic", "Analytic"),
            ("analytic_kpi", "Analytic & KPI"),
        ],
        string="Level of Control",
        required=True,
        default="analytic",
    )
    unmatched_account_policy = fields.Selection(
        selection=[
            ("error", "Block (must be in template)"),
            ("skip", "Allow (pass through)"),
        ],
        required=True,
        default="error",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_currency_id",
    )
    allocated_amount = fields.Monetary(
        string="Total Budget",
        required=True,
        help="Total amount that must be distributed on the Budget Control lines.",
    )

    @api.depends(
        "analytic_account_id",
        "analytic_account_id.company_id.currency_id",
        "analytic_account_id.budget_company_ids.currency_id",
    )
    def _compute_currency_id(self):
        for setup in self:
            analytic = setup.analytic_account_id
            setup.currency_id = (
                analytic.currency_id
                or analytic.budget_company_ids[:1].currency_id
                or self.env.company.currency_id
            )

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for setup in self:
            if setup.date_from and setup.date_to and setup.date_from > setup.date_to:
                raise ValidationError(
                    self.env._("Lifetime start date must be before its end date.")
                )

    @api.constrains("allocated_amount")
    def _check_allocated_amount(self):
        if self.filtered(lambda setup: setup.allocated_amount < 0):
            raise ValidationError(self.env._("Total Budget cannot be negative."))

    def action_create_lifetime_budget(self):
        """Create the dedicated Period and draft Control in one transaction."""
        self.ensure_one()
        analytic = self.analytic_account_id
        with self.env.cr.savepoint():
            period = analytic._create_lifetime_budget_period(
                {
                    "name": self.name,
                    "bm_date_from": self.date_from,
                    "bm_date_to": self.date_to,
                    "template_id": self.template_id.id,
                    "control_budget": True,
                    "plan_date_range_type_id": self.plan_date_range_type_id.id,
                    "control_level": self.control_level,
                    "unmatched_account_policy": self.unmatched_account_policy,
                    "company_ids": [Command.set(analytic.budget_company_ids.ids)],
                }
            )
            control = self.env["budget.control"].create(
                {
                    "name": self.name,
                    "analytic_account_id": analytic.id,
                    "budget_period_id": period.id,
                    "plan_date_range_type_id": self.plan_date_range_type_id.id,
                    "currency_id": self.currency_id.id,
                    "allocated_amount": self.allocated_amount,
                    "use_all_kpis": True,
                }
            )
            control.prepare_budget_control_matrix()
        return {
            "name": self.env._("Lifetime Budget Control"),
            "type": "ir.actions.act_window",
            "res_model": "budget.control",
            "view_mode": "form",
            "res_id": control.id,
        }
