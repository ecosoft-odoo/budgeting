# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .res_company import BUDGET_INVENTORY_ACTUAL_SOURCE


class StockMove(models.Model):
    _inherit = "stock.move"

    budget_actual_source = fields.Selection(
        selection=BUDGET_INVENTORY_ACTUAL_SOURCE,
        required=True,
        default="bill",
        readonly=True,
        copy=True,
        help="Recognition policy captured when the stock move is confirmed. "
        "Returns preserve the source move's policy.",
    )

    @api.model
    def _prepare_budget_actual_source(self, product, company):
        if not product or not product.is_storable:
            return "bill"
        return product.categ_id._get_budget_inventory_actual_source(company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "budget_actual_source" in vals:
                continue
            product = self.env["product.product"].browse(vals.get("product_id"))
            company = self.env["res.company"].browse(vals.get("company_id"))
            if not company and vals.get("picking_id"):
                company = (
                    self.env["stock.picking"].browse(vals["picking_id"]).company_id
                )
            vals["budget_actual_source"] = self._prepare_budget_actual_source(
                product, company or self.env.company
            )
        return super().create(vals_list)

    @api.onchange("product_id")
    def _onchange_budget_actual_source(self):
        for move in self.filtered(lambda rec: rec.state == "draft"):
            move.budget_actual_source = move._prepare_budget_actual_source(
                move.product_id, move.company_id or self.env.company
            )

    def _snapshot_budget_actual_source(self):
        for move in self.filtered(
            lambda rec: rec.state == "draft" and not rec.origin_returned_move_id
        ):
            source = move._prepare_budget_actual_source(
                move.product_id, move.company_id or self.env.company
            )
            if move.budget_actual_source != source:
                move.budget_actual_source = source

    def _should_valuation_affect_budget(self):
        """Apply the captured inventory policy to the valuation event."""
        self.ensure_one()
        policy_move = self.origin_returned_move_id or self
        return (
            policy_move.budget_actual_source == "stock_issue"
            and super()._should_valuation_affect_budget()
        )

    def _action_confirm(self, merge=True, merge_into=False):
        self._snapshot_budget_actual_source()
        return super()._action_confirm(merge=merge, merge_into=merge_into)

    @api.constrains("budget_actual_source", "product_id")
    def _check_budget_actual_source_valuation(self):
        for move in self.filtered(
            lambda rec: rec.budget_actual_source == "stock_issue"
        ):
            if (
                not move.product_id.is_storable
                or move.product_id.categ_id.property_valuation != "real_time"
            ):
                raise ValidationError(
                    self.env._(
                        "Stock Issue budget actual requires automated inventory "
                        "valuation and a storable product. Product '%(product)s' "
                        "uses category '%(category)s'.",
                        product=move.product_id.display_name,
                        category=move.product_id.categ_id.display_name,
                    )
                )

    @api.depends(
        "picking_id.picking_type_id.budget_commit",
        "state",
        "budget_actual_source",
    )
    def _compute_can_commit(self):
        res = super()._compute_can_commit()
        bill_mode_moves = self.filtered(
            lambda move: move.budget_actual_source != "stock_issue"
        )
        bill_mode_moves.update({"can_commit": False})
        return res

    def recompute_budget_move(self):
        """After recomputing ST commit, sync lot-traced PO uncommit.

        Piggybacks on the existing stock budget recompute hook so that
        PO uncommit is always in sync with the current lot assignments,
        covering confirm, lots-change, validate, and cancel transitions.
        """
        res = super().recompute_budget_move()
        outgoing = self.mapped("picking_id").filtered(
            lambda p: p.picking_type_code != "incoming"
            and p.picking_type_id.budget_commit
        )
        for picking in outgoing:
            picking._sync_lot_traced_po_uncommit()
        return res
