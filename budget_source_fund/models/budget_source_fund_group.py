# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetSourceFundGroup(models.Model):
    _name = "budget.source.fund.group"
    _inherit = ["mail.thread"]
    _description = "Source of Fund Group"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        readonly=True,
    )
    fund_line = fields.One2many(
        comodel_name="budget.source.fund",
        inverse_name="fund_group_id",
    )
