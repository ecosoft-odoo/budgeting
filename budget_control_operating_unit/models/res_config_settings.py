# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    group_access_all_ou_transfer_from = fields.Boolean(
        string="Access all operating unit - Transfer From",
        implied_group="budget_control_operating_unit.group_access_all_ou_transfer_from",
    )
    group_access_all_ou_transfer_to = fields.Boolean(
        string="Access all operating unit - Transfer To",
        implied_group="budget_control_operating_unit.group_access_all_ou_transfer_to",
    )
