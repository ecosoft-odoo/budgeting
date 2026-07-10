# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountAssetLine(models.Model):
    _inherit = "account.asset.line"

    def _setup_move_data(self, depreciation_date):
        move_data = super()._setup_move_data(depreciation_date)
        move_data["not_affect_budget"] = self.asset_id.not_affect_budget
        return move_data

    def _setup_move_line_data(self, depreciation_date, account, ml_type, move):
        """
        Set not_affect_budget on move lines:
        - Depreciation line (credit): always True
            - no analytic, would fail budget validation
        - Expense line (debit): follow asset's not_affect_budget flag
        """
        res = super()._setup_move_line_data(depreciation_date, account, ml_type, move)
        if ml_type == "depreciation":
            res["not_affect_budget"] = True
        elif self.asset_id.not_affect_budget:
            res["not_affect_budget"] = True
        return res
