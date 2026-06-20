# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

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
