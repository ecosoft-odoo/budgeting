# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrExpenseAdvanceLine(models.Model):
    _inherit = "hr.expense.advance.line"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        compute="_compute_operating_unit",
        readonly=False,
        store=True,
    )

    @api.depends("expense_id")
    def _compute_operating_unit(self):
        for rec in self:
            rec.operating_unit_id = (
                not rec.operating_unit_id and rec.expense_id.operating_unit_id
            )
