# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class BudgetPeriod(models.Model):
    _name = "budget.period"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Budget Period"

    name = fields.Char(required=True, tracking=True)
    budget_scope = fields.Selection(
        selection=[
            ("fiscal", "Fiscal Period"),
            ("lifetime", "Lifetime"),
        ],
        required=True,
        default="fiscal",
        index=True,
        tracking=True,
        help="Fiscal periods are selected by document date. Lifetime periods are "
        "selected only for their assigned analytic account, so they "
        "may safely overlap fiscal years.",
    )
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
    company_ids = fields.Many2many(
        comodel_name="res.company",
        relation="budget_period_company_rel",
        column1="budget_period_id",
        column2="company_id",
        string="Companies",
        help="Restrict this period to specific companies. Empty = all companies.",
    )

    @api.constrains("bm_date_from", "bm_date_to")
    def _check_period_dates(self):
        for period in self:
            if period.bm_date_from > period.bm_date_to:
                raise ValidationError(
                    self.env._("Budget Period start date must be before its end date.")
                )

    @api.constrains("budget_scope", "bm_date_from", "bm_date_to", "company_ids")
    def _check_fiscal_period_overlap(self):
        """A date belongs to one fiscal period per company. Periods overlap
        when they share a company, or one is a parent company of the other,
        or one of them has no company (all companies)."""
        Company = self.env["res.company"].sudo().with_context(active_test=False)
        for period in self.sudo().filtered(lambda p: p.budget_scope == "fiscal"):
            domain = [
                ("id", "!=", period.id),
                ("budget_scope", "=", "fiscal"),
                ("bm_date_from", "<=", period.bm_date_to),
                ("bm_date_to", ">=", period.bm_date_from),
            ]
            if period.company_ids:
                companies = period.company_ids.parent_ids | Company.search(
                    [("id", "child_of", period.company_ids.ids)]
                )
                domain += [
                    "|",
                    ("company_ids", "=", False),
                    ("company_ids", "in", companies.ids),
                ]
            overlap = period.search(domain, limit=1)
            if overlap:
                raise ValidationError(
                    self.env._(
                        "Fiscal Budget Period %(period)s overlaps %(overlap)s "
                        "for the same companies.",
                        period=period.display_name,
                        overlap=overlap.display_name,
                    )
                )

    @api.model
    def _get_fiscal_period(self, date=None, company=None):
        """Return the fiscal period of date for company (default: today and
        the current company), or an empty recordset. A period of a parent
        company also serves its branches."""
        date = fields.Date.to_date(date) if date else fields.Date.context_today(self)
        company = company or self.env.company
        periods = self.search(
            [
                ("budget_scope", "=", "fiscal"),
                ("bm_date_from", "<=", date),
                ("bm_date_to", ">=", date),
                "|",
                ("company_ids", "=", False),
                ("company_ids", "in", company.parent_ids.ids),
            ]
        )
        if len(periods) > 1:
            raise ValidationError(
                self.env._(
                    "Multiple Budget Periods found for date %(date)s.\nPlease ensure "
                    "there is only one Budget Period valid for this date.",
                    date=date,
                )
            )
        return periods
