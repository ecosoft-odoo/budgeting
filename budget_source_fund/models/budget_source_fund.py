# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetSourceFund(models.Model):
    _name = "budget.source.fund"
    _inherit = ["mail.thread"]
    _description = "Source of Fund"
    _order = "name"

    name = fields.Char(required=True, string="Source of Fund")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        readonly=True,
    )
    fund_group_id = fields.Many2one(
        comodel_name="budget.source.fund.group",
        string="Fund Group",
        tracking=True,
    )
    fund_line_ids = fields.One2many(
        comodel_name="budget.source.fund.line",
        inverse_name="fund_id",
        string="Fund Line",
    )

    _sql_constraints = [
        ("unique_name", "UNIQUE(name)", "Group must be unique")
    ]

    def action_open_fund_line(self):
        self.ensure_one()
        action = self.env.ref(
            "budget_source_fund.budget_source_fund_line_action"
        )
        action_dict = action.read()[0]
        action_dict["context"] = {"active_test": True}
        return action_dict
