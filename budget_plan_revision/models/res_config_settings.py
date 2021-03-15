# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    keep_origin_plan = fields.Boolean(
        string="Keep origin plan",
        implied_group="budget_plan_revision.keep_origin_plan",
    )
