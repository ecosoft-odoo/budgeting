# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange("retained_move_ids")
    def _onchange_retained_move_ids(self):
        res = super()._onchange_retained_move_ids()
        self.not_affect_budget = bool(self.retained_move_ids)
        return res
