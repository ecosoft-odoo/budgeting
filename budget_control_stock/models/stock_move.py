# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = ["stock.move", "budget.docline.mixin"]
    _budget_date_commit_fields = ["picking_id.date_done", "date"]
    _budget_move_model = "stock.budget.move"
    _doc_rel = "picking_id"
    _no_date_commit_states = ["draft", "cancel"]

    budget_move_ids = fields.One2many(
        comodel_name="stock.budget.move",
        inverse_name="stock_move_id",
        string="Stock Budget Moves",
    )
    account_id = fields.Many2one(
        comodel_name="account.account",
        compute="_compute_account_id",
        help="Expense (COGS) account used for KPI mapping in budget.",
    )

    def _compute_account_id(self):
        for rec in self:
            rec.account_id = rec._get_stock_budget_account()

    def _get_stock_budget_account(self):
        """COGS account for sale-side stock consumption KPI mapping."""
        self.ensure_one()
        product = self.product_id
        if not product:
            return False
        fpos = (
            self.picking_id.partner_id
            and self.picking_id.partner_id.property_account_position_id
        )
        accounts = product.product_tmpl_id.get_product_accounts(fpos)
        return accounts.get("expense") or accounts.get("stock_valuation")

    def _is_outbound_consumption(self):
        """Outbound stock consumption from a sale flow.
        Covers:
          - Delivery to customer (DO) — sale_line_id set, picking outgoing
          - Customer return — sale_line_id set, picking incoming (returns
            reverse the previous consumption)
        Excludes:
          - PO receipts (no sale_line_id) — bill remains the actual source
          - MO consumption / internal transfers / scrap (no sale_line_id)
        """
        self.ensure_one()
        return bool(getattr(self, "sale_line_id", False))

    def _has_budget_controlled_analytic(self):
        """True if at least one analytic in analytic_distribution is linked
        to a budget.period. Without this, trading flows that happen to set
        analytic for cost-center tracking would trigger unintended budget
        commits."""
        self.ensure_one()
        dist = self.analytic_distribution or {}
        if not dist:
            return False
        analytic_ids = [int(a) for a in dist.keys()]
        Analytic = self.env["account.analytic.account"]
        return bool(
            Analytic.search_count(
                [("id", "in", analytic_ids), ("budget_period_id", "!=", False)],
                limit=1,
            )
        )

    def _valid_commit_state(self):
        """Two-stage commit for outbound sale flow:
          - state=assigned: pre-commit using standard_price * qty
          - state=done + picking done: actual using signed SVL value
        Inbound (GR) and sourceless moves are skipped entirely."""
        if not self._is_outbound_consumption():
            return False
        if self.state == "assigned":
            return True
        if self.state == "done" and self.picking_id and self.picking_id.state == "done":
            return True
        return False

    def _required_fields_to_commit(self):
        return super()._required_fields_to_commit() + ["product_id", "picking_id"]

    def _budget_estimate_amount(self):
        """Pre-commit amount when SVL not posted yet (assigned stage).
        Sale outbound estimate = internal cost (standard_price). Picking
        direction is irrelevant for the estimate — the actual stage uses
        signed SVL which encodes direction."""
        self.ensure_one()
        return self.product_id.standard_price * self.product_qty

    def _init_docline_budget_vals(self, budget_vals, analytic_id):
        self.ensure_one()
        percent_analytic = (
            self[self._budget_analytic_field].get(str(analytic_id)) or 100
        )
        if self.state == "done" and self.stock_valuation_layer_ids:
            # Actual stage. Outbound DO: SVL = -X → budget = +X (consume).
            # Customer return: SVL = +X → budget = -X (reverse).
            # → amount = -svl_value.
            svl_value = sum(self.stock_valuation_layer_ids.mapped("value"))
            amount = -svl_value
        else:
            # Pre-commit at assigned (no SVL yet).
            amount = self._budget_estimate_amount()
        budget_vals["amount_currency"] = amount * (percent_analytic / 100)
        budget_vals["tax_ids"] = []
        budget_vals.update({"stock_move_id": self.id})
        return super()._init_docline_budget_vals(budget_vals, analytic_id)

    def _update_template_line(self, budget_move):
        for move in budget_move:
            if move.stock_move_id:
                move.stock_valuation_layer_ids = [
                    (6, 0, move.stock_move_id.stock_valuation_layer_ids.ids)
                ]
        return super()._update_template_line(budget_move)

    def recompute_budget_move(self):
        for move in self:
            move.budget_move_ids.unlink()
            move.commit_budget()

    def _action_assign(self):
        """Pre-commit at reservation (assigned)."""
        res = super()._action_assign()
        to_commit = self.filtered(
            lambda m: m.state == "assigned"
            and m.product_id.categ_id.property_valuation == "real_time"
            and m.analytic_distribution
            and m._is_outbound_consumption()
            and m._has_budget_controlled_analytic()
            and not m.budget_move_ids
        )
        if to_commit:
            to_commit.recompute_budget_move()
        return res

    def _action_done(self, cancel_backorder=False):
        """Flip pre-commit → actual at picking done. SVL is now posted."""
        res = super()._action_done(cancel_backorder=cancel_backorder)
        done_moves = self.filtered(
            lambda m: m.state == "done"
            and m.picking_id
            and m.product_id.categ_id.property_valuation == "real_time"
            and m.analytic_distribution
            and m._is_outbound_consumption()
            and m._has_budget_controlled_analytic()
        )
        if done_moves:
            done_moves.recompute_budget_move()
        return res

    def _action_cancel(self):
        res = super()._action_cancel()
        for move in self.filtered(lambda m: m.budget_move_ids):
            move.budget_move_ids.unlink()
        return res
