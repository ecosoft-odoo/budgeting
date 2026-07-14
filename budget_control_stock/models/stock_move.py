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

    def recompute_budget_move(self):
        budget_field = self._budget_field()
        force_date_commit = self.env.context.get("force_date_commit", False)
        lot_price_moves = self.filtered(
            lambda move: move.picking_id.picking_type_id.budget_price_source
            == "lot_price"
            and move.move_line_ids.filtered("lot_id")
        )
        standard_moves = (self - lot_price_moves).filtered(
            lambda move: move.product_id.tracking == "none"
            or move.move_line_ids.filtered("lot_id")
        )

        # Standard-price moves have identical per-line context and can use the
        # common batch path.  Lot-price moves intentionally remain per lot,
        # because every lot can have a different price and quantity.
        standard_moves.recompute_budget_move_batch()
        for move in standard_moves:
            move.forward_commit()
            move._recommit_via_valuation_lines()

        deferred_moves = self - lot_price_moves - standard_moves
        deferred_moves.mapped(budget_field).unlink()
        for move in deferred_moves:
            move.forward_commit()
            move._recommit_via_valuation_lines()

        for move in lot_price_moves:
            st_date_commit = force_date_commit or move.date_commit
            move[budget_field].unlink()
            lot_lines = move.move_line_ids.filtered("lot_id")
            for lot_line in lot_lines:
                move.with_context(
                    force_date_commit=st_date_commit,
                    budget_lot_price=lot_line.lot_id.standard_price,
                    product_qty=lot_line.quantity_product_uom,
                ).commit_budget()
            move.forward_commit()
            # Re-apply uncommit for posted valuation JEs
            move._recommit_via_valuation_lines()

    def _recommit_via_valuation_lines(self):
        """Re-apply uncommit entries for posted valuation JEs after a recompute."""
        self.ensure_one()
        # For 2-step delivery: PICK has no SVL; valuation is on OUT (dest) move.
        svl_moves = self if self.stock_valuation_layer_ids else self.move_dest_ids
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
