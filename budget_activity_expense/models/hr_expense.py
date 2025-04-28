# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class HRExpense(models.Model):
    _inherit = "hr.expense"

    @api.onchange("activity_id")
    def _onchange_activity_id(self):
        if self.activity_id:
            self.account_id = self.activity_id.account_id

    @api.depends("product_id", "company_id")
    def _compute_account_id(self):
        res = super()._compute_account_id()
        for expense in self:
            if expense.activity_id:
                expense.account_id = expense.activity_id.account_id
        return res

    def _prepare_move_lines_vals(self):
        vals = super()._prepare_move_lines_vals()
        if self.activity_id:
            vals.update({"activity_id": self.activity_id.id})
        return vals
