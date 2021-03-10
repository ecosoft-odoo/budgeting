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

    def get_budget_move(self, doc_type="account", domain=None):
        if doc_type == "commit":
            return self._get_budget_move_commit(domain)
        AccountBudgetMove = self.env["account.budget.move"]
        account_move = AccountBudgetMove.search(domain)
        return account_move
