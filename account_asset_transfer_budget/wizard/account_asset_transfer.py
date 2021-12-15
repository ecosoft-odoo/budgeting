# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountAssetTransfer(models.TransientModel):
    _inherit = "account.asset.transfer"

    def _get_new_move_transfer(self):
        move_value = super()._get_new_move_transfer()
        move_value[
            "not_affect_budget"
        ] = self.transfer_journal_id.not_affect_budget
        return move_value
