# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class RequestDocument(models.Model):
    _inherit = "request.document"

    budget_move_ids = fields.One2many(
        comodel_name="request.budget.move",
        inverse_name="request_document_id",
    )

    def _get_lines_request(self):
        mapping_type = self._get_mapping_type()
        request_line = mapping_type.get(self.request_type, False)
        return request_line

    def _get_mapping_type(self):
        return {
            "expense": "expense_line_ids",
            "purchase_request": "pr_line_ids",
        }

    def recompute_budget_move(self):
        for rec in self:
            request_line = rec._get_lines_request()
            if request_line:
                rec.mapped(request_line).recompute_budget_move()

    def close_budget_move(self):
        for rec in self:
            request_line = rec._get_lines_request()
            if request_line:
                rec.mapped(request_line).close_budget_move()
