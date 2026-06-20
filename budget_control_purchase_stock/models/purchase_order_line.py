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
        for purchase_line in self:
            # Collect active outgoing pickings with lot-traced entries for
            # this line BEFORE clearing, so we can re-apply them afterwards.
            done_pickings = purchase_line.budget_move_ids.filtered(
                lambda m: (
                    m.stock_picking_id
                    and m.stock_picking_id.state in _STOCK_COMMIT_STATES
                    and m.stock_picking_id.id
                    not in self.env.context.get("skip_stock_picking_ids", [])
                )
            ).mapped("stock_picking_id")

            # --- replicate base recompute_budget_move logic ---
            purchase_line.budget_move_ids.unlink()
            purchase_line.commit_budget()
            purchase_line.forward_commit()
            # PO uncommit (lot-traced + non-lot) before invoice uncommit so the
            # qty-cap in _get_qty_commit reflects the reduced commitment.
            done_pickings._apply_po_uncommit_for_line(purchase_line)
            purchase_line.invoice_lines.uncommit_purchase_budget()
