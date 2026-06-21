# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    budget_sale_analytic_plan_id = fields.Many2one(
        comodel_name="account.analytic.plan",
        string="Sale Budget Analytic Plan",
        help="Default analytic plan for auto-created analytic accounts "
        "from sale orders without project",
    )
