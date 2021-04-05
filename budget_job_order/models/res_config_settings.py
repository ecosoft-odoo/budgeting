# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    group_budget_job_order = fields.Boolean(
        string="Use Job Order",
        implied_group="budget_job_order.group_budget_job_order",
    )
