# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetDoclineMixin(models.AbstractModel):
    _inherit = "budget.docline.mixin"

    def _get_amount_convert_currency(
        self, amount_currency, currency, company, date_commit
    ):
        if self[self._doc_rel].manual_currency:
            return amount_currency * (1.0 / self[self._doc_rel].custom_rate)
        return super()._get_amount_convert_currency(
            amount_currency, currency, company, date_commit
        )
