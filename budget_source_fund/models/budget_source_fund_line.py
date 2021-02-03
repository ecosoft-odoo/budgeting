# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetSourceFundLine(models.Model):
    _name = "budget.source.fund.line"
    _inherit = ["mail.thread"]
    _description = "Source of Fund Line"
    _rec_name = "fund_id"

    fund_id = fields.Many2one(comodel_name="budget.source.fund", readonly=True)
    active = fields.Boolean(related="fund_id.active")
    date_from = fields.Date(
        required=True,
        string="From",
        tracking=True,
        states={"draft": [("readonly", False)]},
    )
    date_to = fields.Date(
        required=True,
        string="To",
        tracking=True,
        states={"draft": [("readonly", False)]},
    )
    budget_control_id = fields.Many2one(
        comodel_name="budget.control",
    )
    budget_id = fields.Many2one(
        comodel_name="mis.budget",
        related="budget_control_id.budget_id",
        store=True,
    )
    company_currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="fund_id.company_id.currency_id",
        string="Company Currency",
        readonly=True,
        help="Utility field to fund amount currency",
    )
    amount = fields.Monetary(
        default=0.0,
        currency_field="company_currency_id",
        tracking=True,
        states={"draft": [("readonly", False)]},
    )
    spent = fields.Monetary(
        default=0.0, currency_field="company_currency_id", tracking=True
    )
    state = fields.Selection(related="budget_control_id.state", tracking=True)
