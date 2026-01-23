# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class BudgetPeriod(models.Model):
    _inherit = "budget.period"

    @api.model
    def check_budget_precommit(self, doclines, doc_type="account"):
        budget_moves = False
        if doclines._name == "hr.expense":
            request_documents = doclines.mapped("sheet_id.request_document_id")
            if request_documents:
                budget_moves = request_documents.budget_move_ids
                request_documents.with_context(
                    force_commit=True, check_budget_precommit=True
                ).uncommit_request_budget(doclines)
                budget_moves = request_documents.budget_move_ids - budget_moves
        res = super().check_budget_precommit(doclines, doc_type=doc_type)
        if budget_moves:
            budget_moves.unlink()
        return res
