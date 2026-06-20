# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models

_STOCK_COMMIT_STATES = frozenset(
    {"waiting", "confirmed", "assigned", "partially_available", "done"}
)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _get_lot_source_purchase_lines(self):
        """Return {lot_id (int): purchase.order.line} for outgoing move lines.

        Single batched search. FIFO: oldest receipt wins when a lot appears in
        multiple incoming moves.
        """
        lot_ids = self.move_line_ids.filtered("lot_id").mapped("lot_id").ids
        if not lot_ids:
            return {}
        incoming_mls = self.env["stock.move.line"].search(
            [
                ("lot_id", "in", lot_ids),
                ("state", "=", "done"),
                ("move_id.purchase_line_id", "!=", False),
                ("picking_id.picking_type_code", "=", "incoming"),
            ],
            order="date asc, id asc",
        )
        lot_po_map = {}
        for ml in incoming_mls:
            lid = ml.lot_id.id
            if lid not in lot_po_map:
                lot_po_map[lid] = ml.move_id.purchase_line_id
        return lot_po_map

    def _uncommit_source_po_by_lots(self):
        """Create lot-traced PO uncommit entries for current move lines.

        Aggregates qty per PO line to minimise commit_budget calls.
        Only creates entries when positive commitment remains on the PO line.
        """
        self.ensure_one()
        lot_po_map = self._get_lot_source_purchase_lines()
        if not lot_po_map:
            return
        po_line_qty = {}
        for ml in self.move_line_ids.filtered("lot_id"):
            po_line = lot_po_map.get(ml.lot_id.id)
            if po_line:
                po_line_qty[po_line] = (
                    po_line_qty.get(po_line, 0.0) + ml.quantity_product_uom
                )
        for po_line, qty in po_line_qty.items():
            amount_commit = po_line.amount_commit
            if not amount_commit or not any(
                isinstance(v, int | float) and v > 0 for v in amount_commit.values()
            ):
                continue
            po_line.with_context(product_qty=qty).commit_budget(
                reverse=True,
                stock_picking_id=self.id,
                date=self.date_done or fields.Date.today(),
            )

    def _uncommit_source_po_non_lot(self):
        """Uncommit PO budget for non-lot-tracked outgoing moves via product FIFO.

        For moves on products without lot/serial tracking, finds confirmed PO
        lines with matching product (FIFO by PO id, analytic-agnostic) and
        creates uncommit entries capped by remaining committed amount.

        Analytic is intentionally ignored so that a PO committed under Analytic A
        is still uncommitted when the DO uses Analytic B, mirrors the lot-traced
        approach where lot→receipt→PO tracing overrides analytic alignment.

        Only fires for products with tracking='none' to avoid interfering with
        lot-tracked products that use _uncommit_source_po_by_lots instead.
        """
        self.ensure_one()
        non_lot_moves = self.move_ids.filtered(
            lambda m: m.analytic_distribution and m.product_id.tracking == "none"
        )
        if not non_lot_moves:
            return

        # Aggregate DO qty per product_id (analytic-agnostic)
        product_qty = {}
        for move in non_lot_moves:
            product_qty[move.product_id.id] = (
                product_qty.get(move.product_id.id, 0.0) + move.product_uom_qty
            )

        for product_id, do_qty in product_qty.items():
            po_lines = self.env["purchase.order.line"].search(
                [
                    ("product_id", "=", product_id),
                    ("order_id.state", "in", ["purchase", "done"]),
                ],
                order="order_id asc",
            )
            remaining_qty = do_qty
            for po_line in po_lines:
                if remaining_qty <= 0:
                    break
                amount_commit = po_line.amount_commit
                if not amount_commit:
                    continue
                total_committed = sum(
                    v
                    for v in amount_commit.values()
                    if isinstance(v, int | float) and v > 0
                )
                if not total_committed:
                    continue
                price = po_line.price_unit
                uncommit_qty = (
                    min(remaining_qty, total_committed / price)
                    if price > 0
                    else remaining_qty
                )
                if uncommit_qty <= 0:
                    continue
                po_line.with_context(product_qty=uncommit_qty).commit_budget(
                    reverse=True,
                    stock_picking_id=self.id,
                    date=self.date_done or fields.Date.today(),
                )
                remaining_qty -= uncommit_qty

    def _sync_lot_traced_po_uncommit(self):
        """Full sync of PO uncommit entries for this picking.

        Called from StockMove.recompute_budget_move whenever moves on this
        picking are recomputed. Handles all state transitions:
        - DO confirmed / lots reserved  -> creates PO uncommit entries
        - DO lots changed               -> removes stale, re-creates current
        - DO validated                  -> lots unchanged, entries persist
        - DO cancelled                  -> removes entries, restores PO commit

        PO uncommit is skipped when the DO has no analytic distribution:
        no analytic = no ST commit = no PO uncommit needed.

        Covers two cases:
        - Lot-tracked products: traced via lot -> receipt -> purchase_line
        - Non-lot products (tracking=none): matched by product+analytic FIFO

        After removing entries, any PO lines that lost coverage have their
        invoice uncommit recomputed so the bill cap is corrected.
        """
        self.ensure_one()
        PBM = self.env["purchase.budget.move"]
        stale = PBM.search([("stock_picking_id", "=", self.id)])
        lost_po_lines = stale.mapped("purchase_line_id")
        stale.unlink()

        if self.state in _STOCK_COMMIT_STATES:
            # Only uncommit PO when DO has analytic: no analytic = no ST commit
            # = no PO uncommit. This prevents double-uncommit when a DO without
            # analytic is returned and the same lots are re-used on a new DO.
            if any(m.analytic_distribution for m in self.move_ids):
                self._uncommit_source_po_by_lots()
                self._uncommit_source_po_non_lot()
            covered = PBM.search([("stock_picking_id", "=", self.id)]).mapped(
                "purchase_line_id"
            )
        else:
            covered = self.env["purchase.order.line"]

        # PO lines that lost coverage need their invoice uncommit recalculated
        # (bill cap was based on reduced commitment; now restored).
        lost = lost_po_lines - covered
        if lost:
            lost.with_context(skip_stock_picking_ids=[self.id]).recompute_budget_move()

    def _apply_lot_traced_po_uncommit_for_line(self, purchase_line):
        """Re-apply lot-traced uncommit for one PO line during PO recompute.

        Called from PurchaseOrderLine.recompute_budget_move on a recordset of
        active outgoing pickings that previously held lot-traced entries for
        the given purchase_line.
        """
        for picking in self:
            lot_po_map = picking._get_lot_source_purchase_lines()
            qty = sum(
                ml.quantity_product_uom
                for ml in picking.move_line_ids.filtered("lot_id")
                if lot_po_map.get(ml.lot_id.id) == purchase_line
            )
            if not qty:
                continue
            amount_commit = purchase_line.amount_commit
            if not amount_commit or not any(
                isinstance(v, int | float) and v > 0 for v in amount_commit.values()
            ):
                continue
            purchase_line.with_context(product_qty=qty).commit_budget(
                reverse=True,
                stock_picking_id=picking.id,
                date=picking.date_done or fields.Date.today(),
            )

    def _apply_po_uncommit_for_line(self, purchase_line):
        """Re-apply all uncommit strategies for one PO line during PO recompute.

        Runs lot-traced first (reduces commitment before non-lot cap check).
        """
        self._apply_lot_traced_po_uncommit_for_line(purchase_line)
        self._apply_non_lot_po_uncommit_for_line(purchase_line)

    def _apply_non_lot_po_uncommit_for_line(self, purchase_line):
        """Re-apply non-lot uncommit for one PO line during PO recompute.

        Handles non-lot-tracked products (tracking=none) matched by product only
        (analytic-agnostic FIFO, mirrors lot-traced approach).
        """
        if purchase_line.product_id.tracking != "none":
            return
        for picking in self:
            matching_moves = picking.move_ids.filtered(
                lambda m: m.product_id == purchase_line.product_id
                and m.analytic_distribution
                and m.product_id.tracking == "none"
            )
            if not matching_moves:
                continue
            do_qty = sum(m.product_uom_qty for m in matching_moves)
            amount_commit = purchase_line.amount_commit
            if not amount_commit:
                continue
            total_committed = sum(
                v
                for v in amount_commit.values()
                if isinstance(v, int | float) and v > 0
            )
            if not total_committed:
                continue
            price = purchase_line.price_unit
            uncommit_qty = min(do_qty, total_committed / price) if price > 0 else do_qty
            if uncommit_qty <= 0:
                continue
            purchase_line.with_context(product_qty=uncommit_qty).commit_budget(
                reverse=True,
                stock_picking_id=picking.id,
                date=picking.date_done or fields.Date.today(),
            )
