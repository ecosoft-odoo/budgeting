# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetDoclineMixin(models.AbstractModel):
    _inherit = "budget.docline.mixin"

    def _get_amount_convert_currency(
        self, amount_currency, currency, company, date_commit
    ):
        # Expense and Advance don't have manual_currency.
        # So, we check field first if no field skip it.
        doc_budget = self[self._doc_rel]
        if hasattr(doc_budget, "manual_currency") and doc_budget.manual_currency:
            rate = (
                doc_budget.custom_rate
                if doc_budget.type_currency == "inverse_company_rate"
                else (1.0 / doc_budget.custom_rate)
            )
            return amount_currency * rate
        return super()._get_amount_convert_currency(
            amount_currency, currency, company, date_commit
        )
