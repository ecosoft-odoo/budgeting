# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _prepare_asset_vals(self, aml):
        asset_vals = super()._prepare_asset_vals(aml)
        asset_vals["fund_id"] = aml.fund_id
        return asset_vals
