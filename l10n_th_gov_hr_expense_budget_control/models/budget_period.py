# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class BudgetPeriod(models.Model):
    _inherit = "budget.period"

    @api.model
    def check_budget_precommit(self, doclines, doc_type="account"):
        """If the expense has related purchase request, uncommit first"""
        budget_moves = False
        if doclines._name == "hr.expense" and doclines.filtered("pr_line_id"):
            pr_expense = doclines.filtered("pr_line_id")
            budget_moves = pr_expense.with_context(
                force_commit=True
            ).uncommit_purchase_request_budget()
        res = super().check_budget_precommit(doclines, doc_type=doc_type)
        if budget_moves:
            budget_moves.unlink()
        return res
