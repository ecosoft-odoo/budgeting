# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResProjectPlan(models.Model):
    _name = "res.project.plan"
    _description = "Project Plan"

    project_id = fields.Many2one(
        comodel_name="res.project",
        required=True,
        index=True,
        ondelete="cascade",
    )
    budget_period_id = fields.Many2one(
        comodel_name="budget.period",
        required=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="project_id.currency_id",
    )
    amount = fields.Monetary()
