# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models


class BudgetPeriod(models.Model):
    _inherit = "budget.period"

    def _get_balance_currency(self, company, balance, doc_currency, date_commit):
        doclines = self._context.get("doclines")
        if doclines[doclines._doc_rel].manual_currency:
            return balance * (doclines[doclines._doc_rel].custom_rate)
        return super()._get_balance_currency(
            company, balance, doc_currency, date_commit
        )
