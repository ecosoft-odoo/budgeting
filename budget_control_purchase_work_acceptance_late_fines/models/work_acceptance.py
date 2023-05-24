# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class WorkAcceptance(models.Model):
    _inherit = "work.acceptance"

    def _prepare_late_wa_moves(self, move_type):
        """Late fines must not affect budget"""
        move_dict = super()._prepare_late_wa_moves(move_type)
        for move in move_dict:
            move["not_affect_budget"] = True
        return move_dict
