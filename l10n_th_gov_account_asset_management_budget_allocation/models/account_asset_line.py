# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountAssetLine(models.Model):
    _inherit = "account.asset.line"

    def _setup_move_line_data(self, depreciation_date, account, ml_type, move):
        """Prepare data to be propagated to account.move.line"""
        move_line_data = super()._setup_move_line_data(
            depreciation_date, account, ml_type, move
        )
        if self.env.company.asset_move_line_analytic and ml_type == "depreciation":
            move_line_data.update({"fund_id": self.asset_id.fund_id.id})
        return move_line_data
