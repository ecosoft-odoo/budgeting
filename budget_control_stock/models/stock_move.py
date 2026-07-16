# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError

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
        self._recompute_stock_commit_batch()
        for move in self:
            move.forward_commit()
        # Re-apply all posted valuation JEs in one batch after every stock
        # commitment is ready. This lets uncommit_stock_budget batch the create.
        self._recommit_via_valuation_lines()

    def _recompute_stock_commit_batch(self):
        """Batched clear+commit; lot_price still fans out one commit per lot."""
        doclines = self
        if not doclines:
            return self.env[doclines._budget_model()]
        budget_model = doclines._budget_model()
        preserved_dates = {docline.id: docline.date_commit for docline in doclines}
        doclines.mapped(doclines._budget_field()).unlink()
        lot_lines_by_move = {
            move.id: move.move_line_ids.filtered("lot_id") for move in doclines
        }
        # Preserve the former deferred-lot behavior: a lot-tracked move without
        # reserved lots must not be validated or assigned a commitment date yet.
        commit_candidates = doclines.filtered(
            lambda move: move.product_id.tracking == "none"
            or lot_lines_by_move[move.id]
        )
        for docline in commit_candidates:
            if docline._check_required_analytic():
                raise UserError(self.env._("Please fill analytic account."))
        commit_candidates.prepare_commit_batch(preserved_dates=preserved_dates)
        to_commit = commit_candidates.filtered(
            lambda line: line.can_commit
            and (self.env.context.get("force_commit") or line._valid_commit_state())
        )
        if not to_commit:
            return self.env[budget_model]
        force_date_commit = self.env.context.get("force_date_commit", False)
        budget_vals = []
        for move in to_commit:
            lot_lines = lot_lines_by_move[move.id]
            st_date_commit = (
                force_date_commit or preserved_dates.get(move.id) or move.date_commit
            )
            if (
                move.picking_id.picking_type_id.budget_price_source == "lot_price"
                and lot_lines
            ):
                for lot_line in lot_lines:
                    budget_vals.extend(
                        move.with_context(
                            force_date_commit=st_date_commit,
                            budget_lot_price=lot_line.lot_id.standard_price,
                            product_qty=lot_line.quantity_product_uom,
                        )._prepare_commit_vals()
                    )
            elif move.product_id.tracking == "none" or lot_lines:
                # Non-lot product: commit immediately.
                # Lot-tracked product with lots reserved: commit using product qty.
                # Lot-tracked product with no lots yet: defer to action_assign so
                # lot-traced PO uncommit can balance the commit in the same pass.
                budget_vals.extend(
                    move.with_context(
                        force_date_commit=st_date_commit
                    )._prepare_commit_vals()
                )
        if not budget_vals:
            return self.env[budget_model]
        budget_moves = self.env[budget_model].create(budget_vals)
        return to_commit._update_template_line_batch(budget_moves)

    def _recompute_budget_move_sequential(self):
        """Former per-record recompute, kept for parity tests only."""
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
                move.with_context(force_date_commit=st_date_commit).commit_budget()
            move.forward_commit()
            move._recommit_via_valuation_lines()

    def _recommit_via_valuation_lines(self):
        """Re-apply uncommit entries for posted valuation JEs after a recompute."""
        # For 2-step delivery: PICK has no SVL; valuation is on OUT (dest) move.
        direct_svl_moves = self.filtered("stock_valuation_layer_ids")
        svl_moves = direct_svl_moves | (self - direct_svl_moves).mapped("move_dest_ids")
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
