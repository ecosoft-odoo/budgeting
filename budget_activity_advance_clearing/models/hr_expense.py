# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class HRExpense(models.Model):
    _inherit = "hr.expense"

    @api.onchange("activity_id")
    def _onchange_activity_id(self):
        super()._onchange_activity_id()
        if self.advance:
            self.account_id = self.product_id.property_account_expense_id
