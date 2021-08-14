# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    budget_move_ids = fields.One2many(
        comodel_name="purchase.budget.move",
        inverse_name="purchase_id",
        string="Purchase Budget Moves",
    )

    # Allow trigger, because purchase order line is editable even when approved.
    @api.constrains("order_line")
    def recompute_budget_move(self):
        self.mapped("order_line").recompute_budget_move()

    def close_budget_move(self):
        self.mapped("order_line").close_budget_move()

    def write(self, vals):
        """
        - Commit budget when state changes to purchase
        - Cancel/Draft document should delete all budget commitment
        """
        res = super().write(vals)
        if vals.get("state") in ("purchase", "cancel", "draft"):
            doclines = self.mapped("order_line")
            if vals.get("state") in ("cancel", "draft"):
                doclines.write({"date_commit": False})
            doclines.recompute_budget_move()
        return res

    def button_confirm(self):
        res = super().button_confirm()
        self.flush()
        BudgetPeriod = self.env["budget.period"]
        for doc in self:
            BudgetPeriod.check_budget(doc.order_line, doc_type="purchase")
        return res


class PurchaseOrderLine(models.Model):
    _name = "purchase.order.line"
    _inherit = ["purchase.order.line", "budget.docline.mixin"]
    _budget_analytic_field = "account_analytic_id"
    _budget_date_commit_fields = ["order_id.write_date"]
    _budget_move_model = "purchase.budget.move"
    _doc_rel = "order_id"

    budget_move_ids = fields.One2many(
        comodel_name="purchase.budget.move",
        inverse_name="purchase_line_id",
        string="Purchase Budget Moves",
    )
    account_id = fields.Many2one(
        comodel_name="account.account",
        compute="_compute_account_id",
    )

    def _compute_account_id(self):
        for rec in self:
            rec.account_id = rec._get_po_line_account()

    def recompute_budget_move(self):
        for purchase_line in self:
            purchase_line.budget_move_ids.unlink()
            # Commit on purchase order
            purchase_line.commit_budget()
            # Uncommitted on invoice confirm
            purchase_line.invoice_lines.uncommit_purchase_budget()

    def _get_po_line_account(self):
        fpos = self.order_id.fiscal_position_id
        account = self.product_id.product_tmpl_id.get_product_accounts(fpos)[
            "expense"
        ]
        return account

    def _init_docline_budget_vals(self, budget_vals):
        self.ensure_one()
        product_qty = self.product_qty
        if "product_qty" in budget_vals and budget_vals.get("product_qty"):
            product_qty = budget_vals.pop("product_qty")
        budget_vals["amount_currency"] = self.price_unit * product_qty
        budget_vals["tax_ids"] = self.taxes_id.ids
        # Document specific vals
        budget_vals.update(
            {
                "purchase_line_id": self.id,
                "analytic_tag_ids": [(6, 0, self.analytic_tag_ids.ids)],
            }
        )
        return super()._init_docline_budget_vals(budget_vals)

    def _valid_commit_state(self):
        states = ["purchase", "done"]
        return self.state in states
