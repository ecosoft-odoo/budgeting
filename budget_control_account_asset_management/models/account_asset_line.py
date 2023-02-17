# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountAssetLine(models.Model):
    _inherit = "account.asset.line"

    def _setup_move_data(self, depreciation_date):
        """Users can config account.move affect budget"""
        move_data = super()._setup_move_data(depreciation_date)
        move_data["not_affect_budget"] = self.asset_id.not_affect_budget
        return move_data
