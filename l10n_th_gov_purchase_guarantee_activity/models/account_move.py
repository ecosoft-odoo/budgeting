# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _prepare_guarantee_move_line(self, guarantee):
        move_line_vals = super()._prepare_guarantee_move_line(guarantee)
        move_line_vals["activity_id"] = guarantee.guarantee_method_id.activity_id.id
        return move_line_vals
