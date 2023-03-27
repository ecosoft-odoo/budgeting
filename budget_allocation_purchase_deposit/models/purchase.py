# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.depends("budget_move_ids", "budget_move_ids.date")
    def _compute_commit(self):
        """Move amount commit from deposit to first po line"""
        res = super()._compute_commit()
        for deposit in self.filtered(lambda l: l.is_deposit and l.amount_commit < 0):
            available_lines = deposit.order_id.order_line.filtered(
                lambda l: not l.is_deposit and l.amount_commit > 0
            )
            amount_commit = abs(deposit.amount_commit)
            # Check amount commit each line
            for line in available_lines:
                if amount_commit > 0 and line.amount_commit > 0:
                    amount_to_commit = min(amount_commit, line.amount_commit)
                    deposit.amount_commit += amount_to_commit
                    line.amount_commit -= amount_to_commit
                    amount_commit -= amount_to_commit
        return res
