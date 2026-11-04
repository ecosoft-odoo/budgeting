# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetActivity(models.Model):
    _name = "budget.activity"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Budget Activity"
    _check_company_auto = True
    _rec_names_search = ["name", "keyword_ids"]

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    keyword_ids = fields.Many2many(
        comodel_name="budget.activity.keyword",
        relation="budget_activity_keyword_rel",
        column1="activity_id",
        column2="budget_activity_keyword_id",
        string="Keywords",
        check_company=True,
        help="Optional keyword you may want to assign for search",
    )

    _name_uniq = models.Constraint("UNIQUE(name)", "Name must be unique!")


class BudgetActivityKeyword(models.Model):
    _name = "budget.activity.keyword"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Search budget activity with keyword"

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(
        default=True,
        help="Set active to false to hide the Budget Activity keyword "
        "without removing it.",
    )

    _name_company_unique = models.Constraint(
        "UNIQUE(name, company_id)", "This keyword is already used!"
    )
