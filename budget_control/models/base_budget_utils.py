# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BaseBudgetUtils(models.AbstractModel):
    _name = "base.budget.utils"
    _description = "Base function budget utilization"

    def get_amount_commit(self, doc_type="all", domain=None):
        # Implemention will be in ...
        return 0.0

    def _get_budget_move_commit(self, domain):
        return {}

    def get_budget_move(self, doc_type="all", domain=None):
        """
        this function will return value dictionary following your installed module
        - budget_control (account_budget_move)
        - budget_control_expense (expense_budget_move)
        - budget_control_advance (advance_budget_move)
        - budget_control_purchase (purchase_budget_move)
        - budget_control_purchase_request (purchase_request_budget_move)
        i.e. return {
                'account_budget_move': <object>,
                'expense_budget_move': <object>,
                'advance_budget_move': <object>,
                'purchase_budget_move': <object>,
                'purchase_request_budget_move': <object>,
            }
        """
        budget_move = {}
        if domain is None:
            domain = []
        budget_move_commit = self._get_budget_move_commit(domain)
        if doc_type == "commit":
            return budget_move_commit
        if doc_type == "all":
            budget_move = budget_move_commit
        AccountBudgetMove = self.env["account.budget.move"]
        account_move = AccountBudgetMove.search(domain)
        budget_move["account_budget_move"] = account_move
        return budget_move
