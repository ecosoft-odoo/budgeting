# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class HRExpense(models.Model):
    _inherit = "hr.expense"

    @api.onchange("operating_unit_id")
    def _onchange_operating_unit_id(self):
        if self.advance_line:
            self.advance_line._origin.write(
                {"operating_unit_id": self.operating_unit_id.id}
            )
