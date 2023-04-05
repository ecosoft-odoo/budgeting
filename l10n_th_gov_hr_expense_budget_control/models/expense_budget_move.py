# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class ExpenseBudgetMove(models.Model):
    _inherit = "expense.budget.move"

    @api.depends("expense_id")
    def _compute_source_document(self):
        res = super()._compute_source_document()
        for rec in self.filtered("expense_id.pr_line_id"):
            display_name = rec.expense_id.pr_line_id.request_id.name
            rec.source_document = rec.source_document or display_name
        return res
