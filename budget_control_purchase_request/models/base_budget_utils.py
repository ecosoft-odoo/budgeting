# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BaseBudgetUtils(models.AbstractModel):
    _inherit = "base.budget.utils"

    def _get_budget_move_commit(self, domain):
        budget_move = super()._get_budget_move_commit(domain)
        PurchaseRequestBudgetMove = self.env["purchase.request.budget.move"]
        purchase_request_move = PurchaseRequestBudgetMove.search(domain)
        budget_move["purchase_request_budget_move"] = purchase_request_move
        return budget_move

    def get_budget_move(self, doc_type="all", domain=None):
        PurchaseRequestBudgetMove = self.env["purchase.request.budget.move"]
        if doc_type == "purchase_request":
            purchase_request_move = PurchaseRequestBudgetMove.search(domain)
            return {"purchase_request_budget_move": purchase_request_move}
        return super().get_budget_move(doc_type, domain)
