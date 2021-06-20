# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    budget_control_plan_readonly = fields.Selection(
        [("current", "Current Month"), ("last", "Last Month")],
        string="Control Plan - Readonly to",
        default="current",
        help="If checked, all budget moves amount will include tax",
    )
