# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    asset_not_affect_budget = fields.Boolean(
        string="Asset - Not Affect Budget",
        default=True,
        help="If checked, asset will not affect budget",
    )
