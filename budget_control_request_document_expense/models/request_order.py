# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class RequestOrder(models.Model):
    _inherit = "request.order"

    def action_approve(self):
        """Add amount each line in JSON"""
        res = super().action_approve()
        for doc in self:
            for line in doc.line_ids:
                request_line = line._get_lines_request()
                line.line_data_amount = [
                    {doc_line.id: doc_line.total_amount_company}
                    for doc_line in request_line
                ]
        return res

    def clear_data_amount(self):
        return self.mapped("line_ids").write({"line_data_amount": False})

    def action_cancel(self):
        self.clear_data_amount()
        return super().action_cancel()

    def action_draft(self):
        self.clear_data_amount()
        return super().action_draft()
