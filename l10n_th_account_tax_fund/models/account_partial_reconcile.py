# Copyright 2022 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import models


class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    def _update_budget_data(self, line_value, line_data):
        res = super()._update_budget_data(line_value, line_data)
        res.update(
            {
                "fund_id": line_data.fund_id.id,
            }
        )
        return res
