# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class ResProject(models.Model):
    _inherit = "res.project"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        compute="_compute_project_operating_unit",
        store=True,
    )

    @api.depends("department_id")
    def _compute_project_operating_unit(self):
        for rec in self:
            rec.operating_unit_id = rec.department_id.operating_unit_id
