# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

# Mirrors COMMIT_STATES in budget_control_stock
_STOCK_COMMIT_STATES = frozenset(
    {"waiting", "confirmed", "assigned", "partially_available", "done"}
)


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def recompute_budget_move(self):
        """Re-apply lot-traced DO uncommits in the correct order.

        The base recompute sequence is:
          1. clear all budget moves
          2. commit (debit)
          3. forward commit
          4. invoice uncommit (capped by remaining)

        Lot-traced uncommit must be inserted between steps 3 and 4 so the
        qty-cap in _get_qty_commit sees the already-reduced commitment when
        the invoice uncommit runs.
        """
        skip_stock_picking_ids = self.env.context.get("skip_stock_picking_ids", [])
        # Snapshot pickings before the batch unlink wipes the rows they come from.
        done_pickings_by_line = {}
        for purchase_line in self:
            done_pickings_by_line[purchase_line.id] = (
                purchase_line.budget_move_ids.filtered(
                    lambda m: (
                        m.stock_picking_id
                        and m.stock_picking_id.state in _STOCK_COMMIT_STATES
                        and m.stock_picking_id.id not in skip_stock_picking_ids
                    )
                ).mapped("stock_picking_id")
            )

        self.recompute_budget_move_batch()
        for purchase_line in self:
            purchase_line.forward_commit()
            # PO uncommit before invoice uncommit so the qty-cap reflects the
            # reduced commitment.
            done_pickings_by_line[purchase_line.id]._apply_po_uncommit_for_line(
                purchase_line
            )
            purchase_line.invoice_lines.uncommit_purchase_budget()
