# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BaseBudgetUtils(models.AbstractModel):
    _inherit = "base.budget.utils"

    def _get_budget_move_commit(self, domain):
        budget_move = super()._get_budget_move_commit(domain)
        AdvanceBudgetMove = self.env["advance.budget.move"]
        advance_move = AdvanceBudgetMove.search(domain)
        if not advance_move:
            return budget_move
        budget_move["advance_budget_move"] = advance_move
        return budget_move

    def get_budget_move(self, doc_type="account", domain=None):
        AdvanceBudgetMove = self.env["advance.budget.move"]
        if doc_type == "advance":
            advance_move = AdvanceBudgetMove.search(domain)
            return advance_move
        return super().get_budget_move(doc_type, domain)
