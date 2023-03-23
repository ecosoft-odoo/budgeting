# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountAssetRemove(models.TransientModel):
    _inherit = "account.asset.remove"

    def _get_removal_data(self, asset, residual_value):
        move_lines = super()._get_removal_data(asset, residual_value)
        if self.env.company.asset_move_line_analytic:
            fund_id = asset.fund_id.id
            move_lines = [
                (
                    ml[0],
                    ml[1],
                    {
                        **ml[2],
                        "fund_id": fund_id,
                    },
                )
                for ml in move_lines
            ]
        return move_lines
