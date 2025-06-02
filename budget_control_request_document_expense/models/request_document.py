# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class RequestDocument(models.Model):
    _inherit = "request.document"

    def _get_origin_lines(self):
        vals = super()._get_origin_lines()
        vals["expense"] = "expense_sheet_ids.expense_line_ids"
        return vals

    def _get_data_amount(self, request_line):
        if request_line._name == "hr.expense":
            data_amount = [
                {doc_line.id: doc_line.total_amount_currency}
                for doc_line in request_line
            ]
            return data_amount
        return super()._get_data_amount(request_line)

    def uncommit_request_budget(self, request_line):
        res = super().uncommit_request_budget(request_line)
        budget_move = request_line[request_line._budget_move_field]
        # Expense with state approve, posted or done will auto close budget
        if self.env.context.get("reverse_precommit") or (
            request_line._name == "hr.expense"
            and budget_move
            and request_line[request_line._doc_rel].approval_state
            in ["approve", "post", "done"]
        ):
            budget_moves = self.close_budget_move()
            return budget_moves
        return res
