# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    budget_period_id = fields.Many2one(comodel_name="budget.period")
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
        help="Budget commit date must conform with this date",
    )
    bm_date_to = fields.Date(
        string="Date To",
        compute="_compute_bm_date",
        store=True,
        readonly=False,
        help="Budget commit date must conform with this date",
    )
    auto_adjust_date_commit = fields.Boolean(
        string="Auto Adjust Commit Date",
        help="Date From and Date To is used to determine valid date range of "
        "this analytic account when using with budgeting system. If this data range "
        "is setup, but the budget system set date_commit out of this date range "
        "it it can be adjusted automatically.",
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
        string="Balance",
        compute="_compute_amount_budget_info",
        help="Balance = Total Budget - Consumed",
    )

    def _compute_amount_budget_info(self):
        for rec in self:
            rec.amount_budget = sum(
                rec.budget_control_ids.mapped("amount_budget")
            )
            rec.amount_consumed = sum(
                rec.budget_control_ids.mapped("amount_consumed")
            )
            rec.amount_balance = sum(
                rec.budget_control_ids.mapped("amount_balance")
            )

    def next_year_analytic(self):
        """ Find next analytic from analytic date_to + 1 """
        next_analytics = self.env["account.analytic.account"]
        for rec in self:
            dimension_analytic = rec.department_id or rec.project_id
            next_date_range = rec.bm_date_to + relativedelta(days=1)
            next_analytic = dimension_analytic.analytic_account_ids.filtered(
                lambda l: l.bm_date_from == next_date_range
            )
            if not next_analytic:
                raise UserError(
                    _(
                        "{}, No analytic for the next date {}.".format(
                            rec.display_name, next_date_range
                        )
                    )
                )
            next_analytics |= next_analytic
        return next_analytics

    def _check_budget_control_status(self, budget_period_id=False):
        """ Warning for budget_control on budget_period, but not in controlled """
        domain = [("analytic_account_id", "in", self.ids)]
        if budget_period_id:
            domain.append(("budget_period_id", "=", budget_period_id))
        budget_controls = self.env["budget.control"].search(domain)
        # Find analytics has no budget_contol
        bc_analytic_ids = budget_controls.mapped("analytic_account_id").ids
        no_bc_analytic_ids = list(set(self.ids) - set(bc_analytic_ids))
        if no_bc_analytic_ids:
            no_bc_analytics = self.browse(no_bc_analytic_ids)
            names = no_bc_analytics.mapped("display_name")
            raise UserError(
                _("Following analytics has no budget control " "sheet:\n%s")
                % ", ".join(names)
            )
        budget_not_controlled = budget_controls.filtered_domain(
            [("state", "!=", "done")]
        )
        if budget_not_controlled:
            names = budget_not_controlled.mapped(
                "analytic_account_id.display_name"
            )
            raise UserError(
                _(
                    "Budget control sheet for following analytics are not in "
                    "control:\n%s"
                )
                % ", ".join(names)
            )

    @api.depends("budget_period_id")
    def _compute_bm_date(self):
        """Default effective date, but changable"""
        for rec in self:
            rec.bm_date_from = rec.budget_period_id.bm_date_from
            rec.bm_date_to = rec.budget_period_id.bm_date_to

    def _auto_adjust_date_commit(self, docline):
        self.ensure_one()
        if self.auto_adjust_date_commit:
            if self.bm_date_from and self.bm_date_from > docline.date_commit:
                docline.date_commit = self.bm_date_from
            elif self.bm_date_to and self.bm_date_to < docline.date_commit:
                docline.date_commit = self.bm_date_to
