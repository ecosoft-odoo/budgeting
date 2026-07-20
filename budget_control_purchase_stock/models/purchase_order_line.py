# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .res_company import BUDGET_INVENTORY_ACTUAL_SOURCE

# Mirrors COMMIT_STATES in budget_control_stock
_STOCK_COMMIT_STATES = frozenset(
    {"waiting", "confirmed", "assigned", "partially_available", "done"}
)
_STOCK_PICKINGS_CONTEXT_KEY = "budget_stock_pickings_by_purchase_line"
_SKIP_ACTUAL_SOURCE_RESOLVE = "skip_budget_actual_source_resolve"


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_confirm(self):
        """Freeze the recognition policy before creating the PO commitment."""
        self.mapped("order_line")._snapshot_budget_actual_source()
        return super().button_confirm()


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    budget_actual_source = fields.Selection(
        selection=BUDGET_INVENTORY_ACTUAL_SOURCE,
        required=True,
        default="bill",
        readonly=True,
        copy=True,
        help="Recognition policy captured when the PO is confirmed. "
        "Non-storable products always use Vendor Bill.",
    )

    @api.model
    def _prepare_budget_actual_source(self, product, company):
        if not product or not product.is_storable:
            return "bill"
        return product.categ_id._get_budget_inventory_actual_source(company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            product = self.env["product.product"].browse(vals.get("product_id"))
            order = self.env["purchase.order"].browse(vals.get("order_id"))
            company = order.company_id or self.env.company
            vals["budget_actual_source"] = self._prepare_budget_actual_source(
                product, company
            )
        return super().create(vals_list)

    def write(self, vals):
        """Keep the snapshot aligned when an editable approved line changes."""
        if self.env.context.get(_SKIP_ACTUAL_SOURCE_RESOLVE):
            return super().write(vals)
        policy_fields = {"product_id", "order_id", "budget_actual_source"}
        if not policy_fields.intersection(vals):
            return super().write(vals)
        if len(self) > 1:
            for line in self:
                line.write(vals)
            return True
        vals = vals.copy()
        product = (
            self.env["product.product"].browse(vals["product_id"])
            if "product_id" in vals
            else self.product_id
        )
        order = (
            self.env["purchase.order"].browse(vals["order_id"])
            if "order_id" in vals
            else self.order_id
        )
        company = order.company_id or self.company_id or self.env.company
        vals["budget_actual_source"] = self._prepare_budget_actual_source(
            product, company
        )
        return super().write(vals)

    @api.onchange("product_id")
    def _onchange_budget_actual_source(self):
        for line in self:
            company = line.order_id.company_id or line.company_id or self.env.company
            line.budget_actual_source = line._prepare_budget_actual_source(
                line.product_id, company
            )

    def _snapshot_budget_actual_source(self):
        for line in self.filtered(lambda rec: not rec.display_type):
            company = line.order_id.company_id or line.company_id or self.env.company
            source = line._prepare_budget_actual_source(line.product_id, company)
            if line.budget_actual_source != source:
                line.with_context(**{_SKIP_ACTUAL_SOURCE_RESOLVE: True}).write(
                    {"budget_actual_source": source}
                )
        self._check_budget_actual_source_valuation()

    @api.constrains("budget_actual_source", "product_id")
    def _check_budget_actual_source_valuation(self):
        """Guard every create/write, including edits after PO confirmation."""
        for line in self.filtered(
            lambda rec: not rec.display_type
            and rec.budget_actual_source == "stock_issue"
        ):
            if (
                not line.product_id.is_storable
                or line.product_id.categ_id.property_valuation != "real_time"
            ):
                raise ValidationError(
                    self.env._(
                        "Stock Issue budget actual requires automated inventory "
                        "valuation and a storable product. Product '%(product)s' "
                        "uses category '%(category)s'.",
                        product=line.product_id.display_name,
                        category=line.product_id.categ_id.display_name,
                    )
                )

    def _get_budget_unit_amount_company_currency(self):
        """Return one PO-UoM unit using the same tax/currency rules as commit."""
        self.ensure_one()
        company = self.order_id.company_id
        line = self.with_company(company)
        budget_vals = line._budget_include_tax(
            {"amount_currency": self.price_unit, "tax_ids": self.taxes_id.ids}
        )
        amount = budget_vals["amount_currency"]
        currency = self.currency_id
        date = (
            self.date_commit
            or self.order_id.date_order
            or fields.Date.context_today(self)
        )
        if currency and currency != company.currency_id:
            amount = currency._convert(amount, company.currency_id, company, date)
        return abs(amount)

    def _get_remaining_budget_commit_qty(self):
        """Return remaining positive commitment as quantity in the PO UoM."""
        self.ensure_one()
        total_committed = sum(
            value
            for value in (self.amount_commit or {}).values()
            if isinstance(value, int | float) and value > 0
        )
        unit_amount = self._get_budget_unit_amount_company_currency()
        return total_committed / unit_amount if unit_amount else 0.0

    def recompute_budget_move(self):
        """Remember stock handoffs, then retain the base batched recompute."""
        pickings_by_line = dict(self.env.context.get(_STOCK_PICKINGS_CONTEXT_KEY, {}))
        for purchase_line in self:
            pickings = purchase_line.budget_move_ids.filtered(
                lambda m: (
                    m.stock_picking_id
                    and m.stock_picking_id.state in _STOCK_COMMIT_STATES
                    and m.stock_picking_id.id
                    not in self.env.context.get("skip_stock_picking_ids", [])
                )
            ).mapped("stock_picking_id")
            pickings_by_line[str(purchase_line.id)] = pickings.ids
        return super(
            PurchaseOrderLine,
            self.with_context(**{_STOCK_PICKINGS_CONTEXT_KEY: pickings_by_line}),
        ).recompute_budget_move()

    def _recompute_budget_move_before_invoice_uncommit(self):
        res = super()._recompute_budget_move_before_invoice_uncommit()
        pickings_by_line = self.env.context.get(_STOCK_PICKINGS_CONTEXT_KEY, {})
        for purchase_line in self:
            self.env["stock.picking"].browse(
                pickings_by_line.get(str(purchase_line.id), [])
            )._apply_po_uncommit_for_line(purchase_line)
        return res
