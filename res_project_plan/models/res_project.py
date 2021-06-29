# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResProject(models.Model):
    _inherit = "res.project"

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        required=True,
        related="company_id.currency_id",
        states={"done": [("readonly", "=", True)]},
        tracking=True,
    )
    plan_amount = fields.Monetary(
        string="Plan Amount",
        compute="_compute_plan_amount",
        currency_field="currency_id",
        help="Total Plan Amount for this project",
    )
    project_plan_ids = fields.One2many(
        comodel_name="res.project.plan",
        inverse_name="project_id",
    )

    @api.depends("project_plan_ids")
    def _compute_plan_amount(self):
        for rec in self:
            rec.plan_amount = sum(rec.project_plan_ids.mapped("amount"))
