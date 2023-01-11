# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BudgetActivity(models.Model):
    _name = "budget.activity"
    _description = "Budget Activity"

    name = fields.Char(
        required=True,
    )
    kpi_id = fields.Many2one(
        comodel_name="budget.kpi",
        index=True,
    )
    active = fields.Boolean(default=True)
    account_id = fields.Many2one(
        comodel_name="account.account",
        string="Account",
        domain=[("deprecated", "=", False)],
        readonly=False,
        index=True,
        required=False,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    keyword_ids = fields.Many2many(
        comodel_name="budget.activity.keyword",
        relation="budget_activity_keyword_rel",
        column1="budget_activity_id",
        column2="budget_activity_keyword_id",
        string="Keyword",
        help="Optional keyword you may want to assign for search",
    )

    _sql_constraints = [
        ("name_uniq", "UNIQUE(name)", "Name must be unique!"),
    ]

    @api.model
    def name_search(self, name, args=None, operator="ilike", limit=100):
        args = args or []
        domain = []
        if name:
            domain = [
                "|",
                "|",
                ("name", operator, name),
                ("keyword_ids", operator, name),
                ("account_id", operator, name),
            ]
        activitys = self.search(domain + args, limit=limit)
        return activitys.name_get()


class BudgetActivityKeyword(models.Model):
    _name = "budget.activity.keyword"
    _description = "Search budget activity with keyword"

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    active = fields.Boolean(
        default=True,
        help="Set active to false to hide the Budget Activity keyword without removing it.",
    )
    _sql_constraints = [
        (
            "name_company_unique",
            "unique(name, company_id)",
            "This keyword is already used!",
        )
    ]
