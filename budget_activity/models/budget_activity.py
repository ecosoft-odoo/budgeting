# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class BudgetActivity(models.Model):
    _name = "budget.activity"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Budget Activity"
    _check_company_auto = True
    _rec_names_search = ["name", "keyword_ids", "account_id"]

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
        check_company=True,
        index=True,
    )
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
        domain=lambda self: self._get_domain_keywords(),
        help="Optional keyword you may want to assign for search",
    )

    _sql_constraints = [
        ("name_uniq", "UNIQUE(name)", "Name must be unique!"),
    ]

    def _get_domain_keywords(self):
        return "company_id and [('company_id', 'in', [company_id] + [False])] or []"

    @api.onchange("account_id")
    def onchange_account_id(self):
        """Not allow edit account after use it in commit budgeting"""
        BudgetPeriod = self.env["budget.period"]
        MonitorReport = self.env["budget.monitor.report"]

        if not self.account_id:
            return

        query = BudgetPeriod._budget_info_query()
        dataset_all = MonitorReport.read_group(
            domain=[("activity", "=", self._origin.name)],
            fields=query["fields"],
            groupby=query["groupby"],
            lazy=False,
            limit=1,
        )
        if dataset_all:
            raise UserError(
                self.env._(
                    "You cannot change the account because "
                    "it is already used in a commit."
                )
            )


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
    _sql_constraints = [
        (
            "name_company_unique",
            "unique(name, company_id)",
            "This keyword is already used!",
        )
    ]
