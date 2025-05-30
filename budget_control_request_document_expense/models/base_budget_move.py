# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetDoclineMixin(models.AbstractModel):
    _inherit = "budget.docline.mixin"

    def _init_docline_budget_vals(self, budget_vals, analytic_id):
        """Use standard budget move but we need commit in request"""
        budget_vals = super()._init_docline_budget_vals(budget_vals, analytic_id)
        if (
            self.env.context.get("alt_budget_move_model") == "request.budget.move"
            and self._name == "hr.expense"
        ):
            budget_vals.pop("expense_id")  # Delete expense reference
            budget_vals["request_document_id"] = self[
                self._doc_rel
            ].request_document_id.id
        return budget_vals
