# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    group_enable_revision = fields.Boolean(
        string="Enable Revision Number",
        implied_group="budget_control_revision.group_enable_revision",
    )
