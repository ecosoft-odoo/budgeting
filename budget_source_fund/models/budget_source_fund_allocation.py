# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetSourceFundAllocation(models.Model):
    _name = "budget.source.fund.allocation"
    _inherit = ["mail.thread"]
    _description = "Source of Fund Allocation"
    _rec_name = "allocation_id"

    allocation_id = fields.Many2one(
        comodel_name="budget.source.fund.plan", required=True
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    budget_control_id = fields.Many2one(
        comodel_name="budget.control",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    budget_period_id = fields.Many2one(
        comodel_name="budget.period",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    budget_id = fields.Many2one(
        comodel_name="mis.budget",
        related="budget_period_id.mis_budget_id",
        store=True,
    )
    date_from = fields.Date(
        required=True,
        string="From",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    date_to = fields.Date(
        required=True,
        string="To",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    company_currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="allocation_id.company_currency_id",
        string="Company Currency",
        readonly=True,
        help="Utility field to fund amount currency",
    )
    amount = fields.Monetary(
        default=0.0,
        currency_field="company_currency_id",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    spent = fields.Monetary(
        default=0.0,
        currency_field="company_currency_id",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    active = fields.Boolean(
        related="allocation_id.active",
        store=True,
    )
    state = fields.Selection(
        related="allocation_id.state",
        tracking=True,
    )
