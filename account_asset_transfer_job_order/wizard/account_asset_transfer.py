# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountAssetTransfer(models.TransientModel):
    _inherit = "account.asset.transfer"

    job_order_id = fields.Many2one(
        comodel_name="budget.job.order",
        string="Job Order",
    )

    @api.model
    def default_get(self, field_list):
        res = super().default_get(field_list)
        from_asset_ids = self.env.context.get("active_ids")
        assets = self.env["account.asset"].browse(from_asset_ids)
        # Prepare default values
        job_order_id = assets.mapped("job_order_id")
        res["job_order_id"] = (
            job_order_id[0].id if len(job_order_id) == 1 else False
        )
        return res

    def _get_move_line_from_asset(self, move_line):
        move_lines = super()._get_move_line_from_asset(move_line)
        move_lines["job_order_id"] = move_line.job_order_id.id
        return move_lines

    def _get_move_line_to_asset(self, to_asset):
        move_lines = super()._get_move_line_to_asset(to_asset)
        move_lines["job_order_id"] = to_asset.job_order_id.id
        return move_lines


class AccountAssetTransferLine(models.TransientModel):
    _inherit = "account.asset.transfer.line"

    job_order_id = fields.Many2one(
        comodel_name="budget.job.order",
        string="Job Order",
    )

    @api.model
    def default_get(self, field_list):
        res = super().default_get(field_list)
        from_asset_ids = self.env.context.get("active_ids")
        assets = self.env["account.asset"].browse(from_asset_ids)
        # Prepare default values
        job_order_id = assets.mapped("job_order_id")
        res["job_order_id"] = (
            job_order_id[0].id if len(job_order_id) == 1 else False
        )
        return res
