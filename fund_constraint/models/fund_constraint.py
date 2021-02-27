# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class FundConstraint(models.Model):
    _name = "fund.constraint"
    _inherit = "mail.thread"
    _description = "Fund Constraint"

    name = fields.Char(required=True)
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        required=True,
        index=True,
    )
    budget_control_id = fields.Many2one(
        comodel_name="budget.control",
        readonly=True,
    )
    budget_period_id = fields.Many2one(
        comodel_name="budget.period",
        related="analytic_account_id.budget_period_id",
        store=True,
    )
    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        required=True,
        index=True,
    )
    fund_amount = fields.Monetary()
    fund_constraint_line = fields.One2many(
        comodel_name="fund.constraint.line",
        inverse_name="fund_constraint_id",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.user.company_id,
        required=False,
        string="Company",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency", related="company_id.currency_id"
    )
    active = fields.Boolean(default=True)
