# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class Department(models.Model):
    _inherit = "hr.department"

    project_ids = fields.One2many(
        comodel_name="res.project",
        inverse_name="department_id",
        copy=False,
        help="Project to which this department is linked "
        "for structure organization.",
    )
