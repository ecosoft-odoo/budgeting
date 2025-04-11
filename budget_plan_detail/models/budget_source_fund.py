# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetSourceFundGroup(models.Model):
    _name = "budget.source.fund.group"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Source of Fund Group"
    _order = "name"

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    fund_ids = fields.One2many(
        comodel_name="budget.source.fund",
        inverse_name="fund_group_id",
    )


class BudgetSourceFund(models.Model):
    _name = "budget.source.fund"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Source of Fund"
    _order = "name"

    name = fields.Char(required=True, string="Source of Fund", tracking=True)
    fund_group_id = fields.Many2one(
        comodel_name="budget.source.fund.group",
        tracking=True,
    )
    objective = fields.Html()
    active = fields.Boolean(
        default=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        ("name_uniq", "UNIQUE(name)", "Name must be unique!"),
    ]

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {}, name=self.env._("%s (copy)") % self.name)
        return super().copy(default)
