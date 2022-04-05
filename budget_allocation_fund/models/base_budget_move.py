# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BaseBudgetMove(models.AbstractModel):
    _inherit = "base.budget.move"

    def _get_where_commitment(self, docline):
        where_query = super()._get_where_commitment(docline)
        where_fund = "fund_id {} {}".format(
            docline.fund_id and "=" or "is", docline.fund_id.id or "null"
        )
        return " and ".join([where_query, where_fund])
