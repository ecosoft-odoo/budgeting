# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

COMMIT_STATES = ["waiting", "confirmed", "assigned", "partially_available", "done"]


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = ["stock.move", "budget.docline.mixin"]
    _budget_date_commit_fields = ["picking_id.date_done", "picking_id.scheduled_date"]
    _budget_move_model = "stock.budget.move"
    _doc_rel = "picking_id"

    budget_move_ids = fields.One2many(
        comodel_name="stock.budget.move",
        inverse_name="move_id",
    )
    account_id = fields.Many2one(
        comodel_name="account.account",
        compute="_compute_account_id",
    )

    def _compute_account_id(self):
        for move in self:
            move.account_id = move._get_stock_move_account()

    def _get_stock_move_account(self):
        self.ensure_one()
        fpos = (
            self.picking_id.partner_id.property_account_position_id
            if self.picking_id and self.picking_id.partner_id
            else False
        )
        accounts = self.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=fpos)
        return accounts.get("expense") or accounts.get("stock_input")

    def _get_budget_commit_source_moves(self):
        """Return the nearest moves owning the valuation budget commitment.

        A valuation layer is created on the final OUT move. In a multi-step
        delivery, however, the budget commitment can belong to an upstream PICK
        move. Returns must follow the original outgoing move and its upstream
        chain instead of the return operation type.
        """
        budget_moves = self.env["stock.move"]
        for move in self:
            candidates = move.origin_returned_move_id or move
            visited = self.env["stock.move"]
            while candidates:
                candidates -= visited
                if not candidates:
                    break
                visited |= candidates
                committed = candidates.filtered(
                    lambda candidate: (
                        candidate.picking_id.picking_type_id.budget_commit
                    )
                )
                budget_moves |= committed
                candidates = (candidates - committed).mapped("move_orig_ids")
        return budget_moves

    def _should_valuation_affect_budget(self):
        """Whether this move's valuation entry should record budget actual."""
        self.ensure_one()
        return bool(self._get_budget_commit_source_moves())

    def recompute_budget_move(self):
        budget_field = self._budget_field()
        force_date_commit = self.env.context.get("force_date_commit", False)
        for move in self:
            st_date_commit = force_date_commit or move.date_commit
            move[budget_field].unlink()
            lot_lines = move.move_line_ids.filtered("lot_id")
            if (
                move.picking_id.picking_type_id.budget_price_source == "lot_price"
                and lot_lines
            ):
                for lot_line in lot_lines:
                    move.with_context(
                        force_date_commit=st_date_commit,
                        budget_lot_price=lot_line.lot_id.standard_price,
                        product_qty=lot_line.quantity_product_uom,
                    ).commit_budget()
            elif move.product_id.tracking == "none" or lot_lines:
                # Non-lot product: commit immediately.
                # Lot-tracked product with lots reserved: commit using product qty.
                # Lot-tracked product with no lots yet: defer to action_assign so
                # lot-traced PO uncommit can balance the commit in the same pass.
                move.with_context(force_date_commit=st_date_commit).commit_budget()
            move.forward_commit()
            # Re-apply uncommit for posted valuation JEs
            move._recommit_via_valuation_lines()

    def _recommit_via_valuation_lines(self):
        """Re-apply uncommit entries for posted valuation JEs after a recompute."""
        self.ensure_one()
        sudo_move = self.sudo()
        # For 2-step delivery: PICK has no SVL; valuation is on OUT (dest) move.
        svl_moves = (
            sudo_move
            if sudo_move.stock_valuation_layer_ids
            else sudo_move.move_dest_ids
        )
        posted_je_lines = svl_moves.stock_valuation_layer_ids.filtered(
            lambda svl: svl.account_move_id and svl.account_move_id.state == "posted"
        ).mapped("account_move_id.line_ids")
        if posted_je_lines:
            posted_je_lines.uncommit_stock_budget()

    def _get_budget_price_unit(self):
        self.ensure_one()
        source = self.picking_id.picking_type_id.budget_price_source
        if source == "lot_price":
            lot_lines = self.move_line_ids.filtered("lot_id")
            if lot_lines:
                total_value = sum(
                    line.lot_id.standard_price * line.quantity_product_uom
                    for line in lot_lines
                )
                total_qty = sum(line.quantity_product_uom for line in lot_lines)
                if total_qty:
                    return total_value / total_qty
        return self.price_unit or self.product_id.standard_price

    def _init_docline_budget_vals(self, budget_vals, analytic_id):
        self.ensure_one()
        if not budget_vals.get("amount_currency", False):
            percent_analytic = self[self._budget_analytic_field].get(str(analytic_id))
            price = (
                self.env.context.get("budget_lot_price")
                or self._get_budget_price_unit()
            )
            product_qty = self.env.context.get("product_qty") or self.product_uom_qty
            budget_vals["amount_currency"] = (
                price * product_qty * (percent_analytic / 100)
            )
        # Document specific vals
        budget_vals.update({"move_id": self.id})
        return super()._init_docline_budget_vals(budget_vals, analytic_id)

    def write(self, vals):
        res = super().write(vals)
        budget_trigger_fields = {
            "product_uom_qty",
            "product_id",
            "analytic_distribution",
            "price_unit",
        }
        if budget_trigger_fields & vals.keys():
            valid_moves = self.filtered(lambda m: m._valid_commit_state())
            if valid_moves:
                valid_moves.recompute_budget_move()
                BudgetPeriod = self.env["budget.period"]
                BudgetPeriod.check_budget(valid_moves, doc_type="stock")
        return res

    @api.depends("picking_id.picking_type_id.budget_commit", "state")
    def _compute_can_commit(self):
        res = super()._compute_can_commit()
        no_commit = self.filtered(
            lambda m: not m.picking_id.picking_type_id.budget_commit
        )
        no_commit.update({"can_commit": False})
        return res

    def _valid_commit_state(self):
        if not self.picking_id.picking_type_id.budget_commit:
            return False
        return self.state in COMMIT_STATES

    def _check_required_analytic(self):
        if not self.picking_id.picking_type_id.budget_commit:
            return False
        return super()._check_required_analytic()

    def _get_included_tax(self):
        return False
