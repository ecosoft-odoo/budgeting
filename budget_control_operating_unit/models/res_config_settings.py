# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    budget_transfer_source_all_ou = fields.Boolean(
        related="company_id.budget_transfer_source_all_ou", readonly=False
    )
    budget_transfer_target_all_ou = fields.Boolean(
        related="company_id.budget_transfer_target_all_ou", readonly=False
    )
