# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, fields, models


class BudgetSourceFund(models.Model):
    _name = "budget.source.fund"
    _inherit = ["mail.thread"]
    _description = "Source of Fund"
    _order = "name"

    name = fields.Char(required=True, string="Source of Fund")
    fund_group_id = fields.Many2one(
        comodel_name="budget.source.fund.group",
        string="Fund Group",
        tracking=True,
        index=True,
    )
    objective = fields.Html()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        readonly=True,
        index=True,
    )

    _sql_constraints = [
        ("name_uniq", "UNIQUE(name)", "Name must be unique!"),
    ]

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {}, name=_("%s (copy)") % self.name)
        return super().copy(default)
