# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    budget_period_id = fields.Many2one(comodel_name="budget.period")
    budget_control_id = fields.Many2one(
        comodel_name="budget.control",
        readonly=True,
        copy=False,
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

    def _check_budget_control_status(self):
        """ Throw error when has budget_control, but not in controlled """
        budget_controls = self.env["budget.control"].search(
            [("analytic_account_id", "in", self.ids), ("state", "!=", "done")]
        )
        if budget_controls:
            names = budget_controls.mapped("analytic_account_id.display_name")
            raise UserError(_("Budget not controlled: %s") % ", ".join(names))

    @api.depends("budget_period_id")
    def _compute_bm_date(self):
        """Default effective date, but changable"""
        for rec in self:
            rec.bm_date_from = rec.budget_period_id.bm_date_from
            rec.bm_date_to = rec.budget_period_id.bm_date_to
