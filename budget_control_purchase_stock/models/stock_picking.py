# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError

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
        lot_ids = (
            self.move_line_ids.filtered(
                lambda line: line.lot_id
                and line.move_id.budget_actual_source == "stock_issue"
            )
            .mapped("lot_id")
            .ids
        )
        if not lot_ids:
            return {}
        incoming_mls = self.env["stock.move.line"].search(
            [
                ("lot_id", "in", lot_ids),
                ("state", "=", "done"),
                ("move_id.purchase_line_id", "!=", False),
                (
                    "move_id.purchase_line_id.budget_actual_source",
                    "=",
                    "stock_issue",
                ),
                ("picking_id.picking_type_code", "=", "incoming"),
                ("company_id", "=", self.company_id.id),
            ],
            order="date asc, id asc",
        )
        lot_po_map = {}
        for ml in incoming_mls:
            lid = ml.lot_id.id
            if lid not in lot_po_map:
                lot_po_map[lid] = ml.move_id.purchase_line_id
        return lot_po_map

    @api.model
    def _batch_po_uncommit(self, pairs):
        """Create reverse purchase budget moves for all pairs in one batch."""
        PurchaseLine = self.env["purchase.order.line"]
        BudgetMove = self.env["purchase.budget.move"]
        if not pairs:
            return BudgetMove
        po_lines = PurchaseLine.union(*(p[0] for p in pairs))
        preserved_dates = {pl.id: pl.date_commit for pl in po_lines}
        for po_line in po_lines:
            if po_line._check_required_analytic():
                raise UserError(self.env._("Please fill analytic account."))
        po_lines.prepare_commit_batch()
        to_commit = po_lines.filtered(
            lambda line: line.can_commit
            and (self.env.context.get("force_commit") or line._valid_commit_state())
        )
        budget_vals = []
        move_period_dates = []
        for po_line, picking, po_qty, extra_ctx in pairs:
            if po_line not in to_commit:
                continue
            ctx = {"product_qty": po_qty}
            if extra_ctx:
                ctx.update(extra_ctx)
            line_vals = po_line.with_context(**ctx)._prepare_commit_vals(
                reverse=True,
                stock_picking_id=picking.id,
                date=picking.date_done or fields.Date.today(),
            )
            period_date = preserved_dates.get(po_line.id) or po_line.date_commit
            budget_vals.extend(line_vals)
            move_period_dates.extend([period_date] * len(line_vals))
        if not budget_vals:
            return BudgetMove
        budget_moves = BudgetMove.create(budget_vals)
        period_dates = dict(zip(budget_moves.ids, move_period_dates, strict=False))
        po_lines._update_template_line_batch(budget_moves, period_dates=period_dates)
        for po_line in to_commit:
            self.env["budget.period"].check_over_returned_budget(po_line)
        return budget_moves

    def _uncommit_source_po_by_lots(self):
        """Create lot-traced PO uncommit entries for current move lines.

        Aggregates qty per PO line to minimise commit_budget calls.
        Only creates entries when positive commitment remains on the PO line.
        """
        self.ensure_one()
        lot_po_map = self._get_lot_source_purchase_lines()
        if not lot_po_map:
            return self.env["purchase.budget.move"]
        po_line_qty = {}
        for ml in self.move_line_ids.filtered(
            lambda line: line.lot_id
            and line.move_id.budget_actual_source == "stock_issue"
        ):
            po_line = lot_po_map.get(ml.lot_id.id)
            if po_line:
                po_line_qty[po_line] = (
                    po_line_qty.get(po_line, 0.0) + ml.quantity_product_uom
                )
        pairs = []
        for po_line, qty in po_line_qty.items():
            amount_commit = po_line.amount_commit
            if not amount_commit or not any(
                isinstance(v, int | float) and v > 0 for v in amount_commit.values()
            ):
                continue
            po_qty = po_line.product_id.uom_id._compute_quantity(
                qty, po_line.product_uom, round=False
            )
            pairs.append((po_line, self, po_qty, {}))
        return self._batch_po_uncommit(pairs)

    def _uncommit_source_po_by_lots_sequential(self):
        """Former per-record lot uncommit, kept for parity tests only."""
        self.ensure_one()
        lot_po_map = self._get_lot_source_purchase_lines()
        if not lot_po_map:
            return
        po_line_qty = {}
        for ml in self.move_line_ids.filtered(
            lambda line: line.lot_id
            and line.move_id.budget_actual_source == "stock_issue"
        ):
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
            po_qty = po_line.product_id.uom_id._compute_quantity(
                qty, po_line.product_uom, round=False
            )
            po_line.with_context(product_qty=po_qty).commit_budget(
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
        approach where lot->receipt->PO tracing overrides analytic alignment.

        Only fires for products with tracking='none' to avoid interfering with
        lot-tracked products that use _uncommit_source_po_by_lots instead.

        """
        self.ensure_one()
        non_lot_moves = self.move_ids.filtered(
            lambda m: m.analytic_distribution
            and m.product_id.tracking == "none"
            and m.budget_actual_source == "stock_issue"
        )
        if not non_lot_moves:
            return self.env["purchase.budget.move"]

        # Aggregate DO qty per product_id (analytic-agnostic)
        product_qty = {}
        for move in non_lot_moves:
            qty = move.product_uom._compute_quantity(
                move.product_uom_qty, move.product_id.uom_id, round=False
            )
            product_qty[move.product_id.id] = (
                product_qty.get(move.product_id.id, 0.0) + qty
            )

        budget_date = (
            max(non_lot_moves.filtered("date_commit").mapped("date_commit"))
            if non_lot_moves.filtered("date_commit")
            else self.date_done or self.scheduled_date
        )
        period = self.env["budget.period"]._get_eligible_budget_period(budget_date)

        pairs = []
        for product_id, do_qty in product_qty.items():
            domain = [
                ("product_id", "=", product_id),
                ("order_id.company_id", "=", self.company_id.id),
                ("order_id.state", "in", ["purchase", "done"]),
                ("qty_received", ">", 0),
                ("budget_actual_source", "=", "stock_issue"),
            ]
            if period:
                domain += [
                    ("date_commit", ">=", period.bm_date_from),
                    ("date_commit", "<=", period.bm_date_to),
                ]
            po_lines = self.env["purchase.order.line"].search(
                domain,
                order="date_order asc, order_id asc, id asc",
            )
            remaining_qty = do_qty
            for po_line in po_lines:
                if remaining_qty <= 0:
                    break
                available_po_qty = po_line._get_remaining_budget_commit_qty()
                if not available_po_qty:
                    continue
                requested_po_qty = po_line.product_id.uom_id._compute_quantity(
                    remaining_qty, po_line.product_uom, round=False
                )
                uncommit_qty = min(requested_po_qty, available_po_qty)
                if uncommit_qty <= 0:
                    continue
                pairs.append((po_line, self, uncommit_qty, {}))
                remaining_qty -= po_line.product_uom._compute_quantity(
                    uncommit_qty, po_line.product_id.uom_id, round=False
                )
        return self._batch_po_uncommit(pairs)

    def _uncommit_source_po_non_lot_sequential(self):
        """Former per-record non-lot uncommit, kept for parity tests only."""
        self.ensure_one()
        non_lot_moves = self.move_ids.filtered(
            lambda m: m.analytic_distribution
            and m.product_id.tracking == "none"
            and m.budget_actual_source == "stock_issue"
        )
        if not non_lot_moves:
            return

        product_qty = {}
        for move in non_lot_moves:
            qty = move.product_uom._compute_quantity(
                move.product_uom_qty, move.product_id.uom_id, round=False
            )
            product_qty[move.product_id.id] = (
                product_qty.get(move.product_id.id, 0.0) + qty
            )

        for product_id, do_qty in product_qty.items():
            domain = [
                ("product_id", "=", product_id),
                ("order_id.company_id", "=", self.company_id.id),
                ("order_id.state", "in", ["purchase", "done"]),
                ("qty_received", ">", 0),
                ("budget_actual_source", "=", "stock_issue"),
            ]
            budget_date = (
                max(non_lot_moves.filtered("date_commit").mapped("date_commit"))
                if non_lot_moves.filtered("date_commit")
                else self.date_done or self.scheduled_date
            )
            period = self.env["budget.period"]._get_eligible_budget_period(budget_date)
            if period:
                domain += [
                    ("date_commit", ">=", period.bm_date_from),
                    ("date_commit", "<=", period.bm_date_to),
                ]
            po_lines = self.env["purchase.order.line"].search(
                domain,
                order="date_order asc, order_id asc, id asc",
            )
            remaining_qty = do_qty
            for po_line in po_lines:
                if remaining_qty <= 0:
                    break
                available_po_qty = po_line._get_remaining_budget_commit_qty()
                if not available_po_qty:
                    continue
                requested_po_qty = po_line.product_id.uom_id._compute_quantity(
                    remaining_qty, po_line.product_uom, round=False
                )
                uncommit_qty = min(requested_po_qty, available_po_qty)
                if uncommit_qty <= 0:
                    continue
                po_line.with_context(product_qty=uncommit_qty).commit_budget(
                    reverse=True,
                    stock_picking_id=self.id,
                    date=self.date_done or fields.Date.today(),
                )
                remaining_qty -= po_line.product_uom._compute_quantity(
                    uncommit_qty, po_line.product_id.uom_id, round=False
                )

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

        Covers two cases for Stock Issue move snapshots:
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
            if any(
                m.analytic_distribution and m.budget_actual_source == "stock_issue"
                for m in self.move_ids
            ):
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
        """Re-apply lot-traced uncommit for one PO line."""
        if purchase_line.budget_actual_source != "stock_issue":
            return self.env["purchase.budget.move"]
        remaining_qty = purchase_line._get_remaining_budget_commit_qty()
        if remaining_qty <= 0:
            return self.env["purchase.budget.move"]
        pairs = []
        for picking in self:
            lot_po_map = picking._get_lot_source_purchase_lines()
            qty = sum(
                ml.quantity_product_uom
                for ml in picking.move_line_ids.filtered(
                    lambda line: line.lot_id
                    and line.move_id.budget_actual_source == "stock_issue"
                )
                if lot_po_map.get(ml.lot_id.id) == purchase_line
            )
            if not qty:
                continue
            po_qty = purchase_line.product_id.uom_id._compute_quantity(
                qty, purchase_line.product_uom, round=False
            )
            pairs.append((purchase_line, picking, po_qty, {}))
            # Stop after the pair that exhausts the PO, matching sequential behavior.
            remaining_qty -= po_qty
            if remaining_qty <= 0:
                break
        return self._batch_po_uncommit(pairs)

    def _apply_lot_traced_po_uncommit_for_line_sequential(self, purchase_line):
        """Former per-record lot-traced re-apply, kept for parity tests only."""
        if purchase_line.budget_actual_source != "stock_issue":
            return
        for picking in self:
            lot_po_map = picking._get_lot_source_purchase_lines()
            qty = sum(
                ml.quantity_product_uom
                for ml in picking.move_line_ids.filtered(
                    lambda line: line.lot_id
                    and line.move_id.budget_actual_source == "stock_issue"
                )
                if lot_po_map.get(ml.lot_id.id) == purchase_line
            )
            if not qty:
                continue
            amount_commit = purchase_line.amount_commit
            if not amount_commit or not any(
                isinstance(v, int | float) and v > 0 for v in amount_commit.values()
            ):
                continue
            po_qty = purchase_line.product_id.uom_id._compute_quantity(
                qty, purchase_line.product_uom, round=False
            )
            purchase_line.with_context(product_qty=po_qty).commit_budget(
                reverse=True,
                stock_picking_id=picking.id,
                date=picking.date_done or fields.Date.today(),
            )

    def _apply_po_uncommit_for_line(self, purchase_line):
        """Re-apply lot and non-lot uncommit for one PO line."""
        self._apply_lot_traced_po_uncommit_for_line(purchase_line)
        self._apply_non_lot_po_uncommit_for_line(purchase_line)

    def _apply_non_lot_po_uncommit_for_line(self, purchase_line):
        """Re-apply non-lot uncommit using a shared remaining PO quantity."""
        if (
            purchase_line.product_id.tracking != "none"
            or purchase_line.budget_actual_source != "stock_issue"
        ):
            return self.env["purchase.budget.move"]
        pairs = []
        remaining_qty = purchase_line._get_remaining_budget_commit_qty()
        for picking in self:
            if remaining_qty <= 0:
                break
            matching_moves = picking.move_ids.filtered(
                lambda m: m.product_id == purchase_line.product_id
                and m.analytic_distribution
                and m.product_id.tracking == "none"
                and m.budget_actual_source == "stock_issue"
            )
            if not matching_moves:
                continue
            do_product_qty = sum(
                m.product_uom._compute_quantity(
                    m.product_uom_qty, m.product_id.uom_id, round=False
                )
                for m in matching_moves
            )
            do_qty = purchase_line.product_id.uom_id._compute_quantity(
                do_product_qty, purchase_line.product_uom, round=False
            )
            uncommit_qty = min(do_qty, remaining_qty)
            if uncommit_qty <= 0:
                continue
            pairs.append((purchase_line, picking, uncommit_qty, {}))
            remaining_qty -= uncommit_qty
        return self._batch_po_uncommit(pairs)

    def _apply_non_lot_po_uncommit_for_line_sequential(self, purchase_line):
        """Former per-record non-lot re-apply, kept for parity tests only."""
        if (
            purchase_line.product_id.tracking != "none"
            or purchase_line.budget_actual_source != "stock_issue"
        ):
            return
        for picking in self:
            matching_moves = picking.move_ids.filtered(
                lambda m: m.product_id == purchase_line.product_id
                and m.analytic_distribution
                and m.product_id.tracking == "none"
                and m.budget_actual_source == "stock_issue"
            )
            if not matching_moves:
                continue
            do_product_qty = sum(
                m.product_uom._compute_quantity(
                    m.product_uom_qty, m.product_id.uom_id, round=False
                )
                for m in matching_moves
            )
            do_qty = purchase_line.product_id.uom_id._compute_quantity(
                do_product_qty, purchase_line.product_uom, round=False
            )
            available_qty = purchase_line._get_remaining_budget_commit_qty()
            if not available_qty:
                continue
            uncommit_qty = min(do_qty, available_qty)
            if uncommit_qty <= 0:
                continue
            purchase_line.with_context(product_qty=uncommit_qty).commit_budget(
                reverse=True,
                stock_picking_id=picking.id,
                date=picking.date_done or fields.Date.today(),
            )
