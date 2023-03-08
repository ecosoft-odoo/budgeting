# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountBudgetMove(models.Model):
    _inherit = "account.budget.move"

    def _get_operating_unit(self):
        return self.env.user.operating_unit_ids

    @api.model
    def _view_account_budget_move(self):
        res = super()._view_account_budget_move()
        # Domain operating unit
        operating_unit_ids = self._get_operating_unit()
        res["domain"] = [("operating_unit_id", "in", operating_unit_ids.ids)]
        return res
