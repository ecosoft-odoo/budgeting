# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetActivityTag(models.Model):
    _name = "budget.activity.tag"
    _description = "Budget Activity Tag"

    name = fields.Char(string="Name", required=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    active = fields.Boolean(
        default=True,
        help="Set active to false to hide the Budget Activity Tag without removing it.",
    )
    _sql_constraints = [
        (
            "name_company_unique",
            "unique(name, company_id)",
            "This tag name is already used!",
        )
    ]


class BudgetActivity(models.Model):
    _name = "budget.activity"
    _description = "Budget Activity"

    name = fields.Char(
        required=True,
    )
    active = fields.Boolean(default=True)
    account_id = fields.Many2one(
        comodel_name="account.account",
        string="Account",
        domain=[("deprecated", "=", False)],
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    code = fields.Char(related="account_id.code")
    tag_ids = fields.Many2many(
        comodel_name="budget.activity.tag",
        relation="budget_activity_tag_rel",
        column1="budget_activity_id",
        column2="budget_activity_tag_id",
        string="Tags",
        help="Optional tags you may want to assign for search",
    )
