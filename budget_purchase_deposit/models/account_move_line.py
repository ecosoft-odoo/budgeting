# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_po_line_amount_commit(self):
        """Purchase deposit is not has amount_commit.
        this function skip filter amount commit for deposit only"""
        if self.purchase_line_id.is_deposit:
            return self.purchase_line_id
        return super()._get_po_line_amount_commit()

    def _check_skip_negative_qty(self):
        """Purchase deposit must be negative qty. this function skip check qty"""
        skip_negative_qty = False
        if self.purchase_line_id.is_deposit:
            skip_negative_qty = True
        return super(
            AccountMoveLine, self.with_context(skip_negative_qty=skip_negative_qty)
        )._check_skip_negative_qty()

    def _get_qty_commit(self, purchase_line):
        """In purchase line deposit is zero qty, This function check qty from invoice instead"""
        if purchase_line.is_deposit:
            return self.quantity
        return super()._get_qty_commit(purchase_line)
