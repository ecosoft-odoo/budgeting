# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import models


class WorkAcceptance(models.Model):
    _inherit = "work.acceptance"

    def _prepare_late_wa_move_line(self, name=False):
        move_line = super()._prepare_late_wa_move_line(name=name)
        # Update analytic_account_id
        analytic_account_ids = self.wa_line_ids.mapped("purchase_line_id.account_analytic_id")
        if len(analytic_account_ids) == 1:
            move_line["analytic_account_id"] = analytic_account_ids
        # Update analytic_tag_ids
        analytic_tag_ids = self.wa_line_ids.mapped("purchase_line_id.analytic_tag_ids")
        if analytic_tag_ids:
            move_line["analytic_tag_ids"] = [(6, 0, analytic_tag_ids.ids)]     
        return move_line
