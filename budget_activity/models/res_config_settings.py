# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    group_budget_activity_tag = fields.Boolean(
        string="Budget Activity Tags",
        implied_group="budget_activity.group_budget_activity_tag",
    )
