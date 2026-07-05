# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class HRExpense(models.Model):
    _inherit = "hr.expense"

    def _get_petty_cash_move_line_dest_vals(self, move_line_name, partner):
        """The petty cash clearing side already commits budget on the
        expense side, so the destination line must not affect budget."""
        vals = super()._get_petty_cash_move_line_dest_vals(move_line_name, partner)
        vals["not_affect_budget"] = True
        return vals
