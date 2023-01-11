# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetJobOrder(models.Model):
    _name = "budget.job.order"
    _description = "Budget Job Order"

    name = fields.Char(
        required=True,
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    analytic_account_ids = fields.Many2many(
        comodel_name="account.analytic.account",
        relation="analytic_job_rel",
        column1="job_order_id",
        column2="analytic_account_id",
        string="Analytic Account",
        index=True,
    )
    _sql_constraints = [
        ("name_uniq", "UNIQUE(name)", "Name must be unique!"),
    ]
