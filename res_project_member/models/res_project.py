# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResProject(models.Model):
    _inherit = "res.project"

    member_ids = fields.Many2many(
        comodel_name="hr.employee",
        relation="employee_project_member_rel",
        column1="project_id",
        column2="employee_id",
        string="Member",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
