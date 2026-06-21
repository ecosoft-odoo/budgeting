# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    budget_sale_analytic_plan_id = fields.Many2one(
        comodel_name="account.analytic.plan",
        related="company_id.budget_sale_analytic_plan_id",
        readonly=False,
    )
