# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    number = fields.Char(default="/", readonly=True)

    @api.model
    def create(self, vals):
        if vals.get("number", "/") == "/":
            number = self.env["ir.sequence"].next_by_code("budget.control")
            vals["number"] = number
        return super().create(vals)
