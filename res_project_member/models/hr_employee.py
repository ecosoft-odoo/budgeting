# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class HrEmployeePrivate(models.Model):
    _inherit = "hr.employee"

    project_ids = fields.Many2many(
        comodel_name="res.project",
        relation="employee_project_member_rel",
        column1="employee_id",
        column2="project_id",
        string="Project",
    )
