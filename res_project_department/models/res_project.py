# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResProject(models.Model):
    _inherit = "res.project"

    department_id = fields.Many2one(
        comodel_name="hr.department",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
