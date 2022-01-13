# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountAssetLine(models.Model):
    _inherit = "account.asset.line"

    def _setup_move_line_data(self, depreciation_date, account, ml_type, move):
        move_line_data = super()._setup_move_line_data(
            depreciation_date, account, ml_type, move
        )
        if ml_type == "expense":
            move_line_data["fund_id"] = self.asset_id.fund_id.id
        return move_line_data
