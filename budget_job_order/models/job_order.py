# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


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
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Analytic Account",
        index=True,
        required=True,
    )
    _sql_constraints = [
        (
            "name_analytic_unique",
            "unique(name, analytic_account_id)",
            "This name is already used by this analytic!",
        )
    ]

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        args = args or []
        if "default_analytic_account_id" in self.env.context:
            job_order_ids = []
            analytic_id = self.env.context["default_analytic_account_id"]
            if analytic_id:
                job_order_ids = self.search(
                    [("analytic_account_id", "=", analytic_id)]
                ).ids
            args += [("id", "in", job_order_ids)]
        return super().name_search(name, args, operator, limit)
