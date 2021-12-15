# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountAssetTransfer(models.TransientModel):
    _inherit = "account.asset.transfer"

    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        string="Fund",
    )

    @api.model
    def default_get(self, field_list):
        res = super().default_get(field_list)
        from_asset_ids = self.env.context.get("active_ids")
        assets = self.env["account.asset"].browse(from_asset_ids)
        # Prepare default values
        fund_id = assets.mapped("fund_id")
        res["fund_id"] = fund_id[0].id if len(fund_id) == 1 else False
        return res

    def _get_move_line_from_asset(self, move_line):
        move_lines = super()._get_move_line_from_asset(move_line)
        move_lines["fund_id"] = move_line.fund_id.id
        return move_lines

    def _get_move_line_to_asset(self, to_asset):
        move_lines = super()._get_move_line_to_asset(to_asset)
        move_lines["fund_id"] = (to_asset.fund_id.id,)
        return move_lines


class AccountAssetTransferLine(models.TransientModel):
    _inherit = "account.asset.transfer.line"

    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        string="Fund",
    )
