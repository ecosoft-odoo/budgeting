# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models


class BudgetPeriod(models.Model):
    _inherit = "budget.period"

    def _get_balance_currency(self, company, balance, doc_currency, date_commit):
        # Expense and Advance don't have manual_currency.
        # So, we check field first if no field skip it.
        doclines = self._context.get("doclines")
        doc_budget = doclines[doclines._doc_rel]
        if hasattr(doc_budget, "manual_currency") and doc_budget.manual_currency:
            return balance * (doc_budget.custom_rate)
        return super()._get_balance_currency(
            company, balance, doc_currency, date_commit
        )
