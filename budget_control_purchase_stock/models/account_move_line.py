# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_qty_commit(self, purchase_line):
        """Cap uncommit qty by remaining PO commitment.

        When part of a PO has already been uncommitted via DO lot tracing,
        the vendor bill must not over-uncommit the remaining balance.
        """
        qty = super()._get_qty_commit(purchase_line)
        amount_commit = purchase_line.amount_commit
        if not amount_commit or not purchase_line.price_unit:
            return qty
        total_remaining = sum(
            v for v in amount_commit.values() if isinstance(v, (int | float)) and v > 0
        )
        if not total_remaining:
            return 0.0
        remaining_qty = total_remaining / purchase_line.price_unit
        return min(qty, remaining_qty)
