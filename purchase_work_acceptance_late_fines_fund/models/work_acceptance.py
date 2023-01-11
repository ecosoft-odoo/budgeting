# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import models


class WorkAcceptance(models.Model):
    _inherit = "work.acceptance"

    def _prepare_late_wa_move_line(self, name=False):
        move_line = super()._prepare_late_wa_move_line(name=name)
        # Update fund_id
        fund_ids = self.wa_line_ids.mapped("purchase_line_id.fund_id")
        if len(fund_ids) == 1:
            move_line["fund_id"] = fund_ids
        return move_line
