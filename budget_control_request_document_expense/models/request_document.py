# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class RequestDocument(models.Model):
    _inherit = "request.document"

    def _get_origin_lines(self):
        vals = super()._get_origin_lines()
        vals["expense"] = "expense_sheet_ids.expense_line_ids"
        return vals

    def uncommit_request_budget(self, request_line):
        res = super().uncommit_request_budget(request_line)
        budget_move = request_line[request_line._budget_move_field]
        # Expense with state approve, posted or done will auto close budget
        if (
            request_line._name == "hr.expense"
            and budget_move
            and request_line[request_line._doc_rel].state in ["approve", "post", "done"]
        ):
            self.close_budget_move()
        return res
