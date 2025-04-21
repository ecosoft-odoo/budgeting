# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    budget_plan_revision_cancel = fields.Selection(
        selection=[
            ("manual", "Manual"),
            ("auto", "Auto"),
        ],
        default="manual",
        help="all budget control will auto/manual cancel before budget plan is revised",
    )
