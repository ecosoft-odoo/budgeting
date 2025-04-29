# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    budget_plan_revision_cancel = fields.Selection(
        related="company_id.budget_plan_revision_cancel", readonly=False
    )
    budget_control_revision_lock_amount = fields.Selection(
        related="company_id.budget_control_revision_lock_amount",
        readonly=False,
    )
