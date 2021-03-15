# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BaseBudgetUtils(models.AbstractModel):
    _inherit = "base.budget.utils"

    def _get_budget_move_commit(self, domain):
        budget_move = super()._get_budget_move_commit(domain)
        ExpenseBudgetMove = self.env["expense.budget.move"]
        expense_move = ExpenseBudgetMove.search(domain)
        budget_move["expense_budget_move"] = expense_move
        return budget_move

    def get_budget_move(self, doc_type="all", domain=None):
        ExpenseBudgetMove = self.env["expense.budget.move"]
        if doc_type == "expense":
            expense_move = ExpenseBudgetMove.search(domain)
            return {"expense_budget_move": expense_move}
        return super().get_budget_move(doc_type, domain)
