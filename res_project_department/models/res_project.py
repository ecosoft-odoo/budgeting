# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class ResProject(models.Model):
    _inherit = "res.project"

    department_id = fields.Many2one(
        comodel_name="hr.department",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    @api.onchange("user_id")
    def _onchange_department_id(self):
        Employee = self.env["hr.employee"]
        employee_ids = Employee.search(
            [("user_id", "in", self.mapped("user_id").ids)]
        )
        for rec in self:
            employee_id = employee_ids.filtered(
                lambda l: l.user_id == rec.user_id
            )
            rec.department_id = employee_id.department_id or False
