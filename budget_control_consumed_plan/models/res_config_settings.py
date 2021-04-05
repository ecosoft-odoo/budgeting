# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    group_manual_date_consumed_plan = fields.Boolean(
        string="Update date manual on consumed plan",
        implied_group="budget_control_consumed_plan.group_manual_date_consumed_plan",
    )
