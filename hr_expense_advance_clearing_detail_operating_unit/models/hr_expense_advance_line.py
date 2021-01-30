# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrExpenseAdvanceLine(models.Model):
    _inherit = "hr.expense.advance.line"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
    )
