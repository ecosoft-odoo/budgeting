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

    def _get_origin_field(self):
        """WA can created from Purchase Order or Expense"""
        return ["purchase_line_id", "expense_id"]

    def _prepare_late_wa_move_line(self, name=False):
        ml_dict = super()._prepare_late_wa_move_line(name=name)
        field_origin = self._get_origin_field()
        wa_lines = self.mapped("wa_line_ids")
        # Get analytic account from original document
        for field in field_origin:
            # Check if field exist in WA
            obj = getattr(wa_lines, field, False)
            if not obj:
                continue
            analytic = obj[obj._budget_analytic_field]
            if analytic:
                ml_dict["analytic_account_id"] = analytic.id
        return ml_dict
