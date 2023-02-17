# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountAssetTransfer(models.TransientModel):
    _inherit = "account.asset.transfer"

    not_affect_budget = fields.Boolean(default=True)

    def _get_move_line_from_asset(self, move_line):
        """Get data fund from origin asset"""
        move_lines = super()._get_move_line_from_asset(move_line)
        move_lines["fund_id"] = move_line.fund_id.id
        return move_lines

    def _get_move_line_to_asset(self, to_asset):
        """Get data fund from new asset"""
        move_lines = super()._get_move_line_to_asset(to_asset)
        move_lines["fund_id"] = to_asset.fund_id.id
        return move_lines

    def _get_new_move_transfer(self):
        move_data = super()._get_new_move_transfer()
        move_data["not_affect_budget"] = self.not_affect_budget
        return move_data


class AccountAssetTransferLine(models.TransientModel):
    _name = "account.asset.transfer.line"
    _inherit = [
        "analytic.dimension.line",
        "account.asset.transfer.line",
        "budget.docline.mixin.base",
    ]
    _analytic_tag_field_name = "analytic_tag_ids"
