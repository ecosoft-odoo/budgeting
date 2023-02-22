# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class PurchaseAdvancePaymentInv(models.TransientModel):
    _inherit = "purchase.advance.payment.inv"

    account_analytic_all = fields.Many2many(
        comodel_name="account.analytic.account",
        compute="_compute_account_analytic_all",
        compute_sudo=True,
    )
    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
    )
    fund_all = fields.Many2many(
        comodel_name="budget.source.fund",
        compute="_compute_fund_all",
        compute_sudo=True,
    )
    analytic_tag_all = fields.Many2many(
        comodel_name="account.analytic.tag",
        compute="_compute_analytic_tag_all",
        compute_sudo=True,
    )

    def _get_purchase_order(self):
        """Get purchase order"""
        active_id = self._context.get("active_id")
        order = self.env["purchase.order"].browse(active_id)
        return order

    @api.depends("purchase_deposit_product_id")
    def _compute_account_analytic_all(self):
        """Compute all analytic account on purchase order"""
        for doc in self:
            order = doc._get_purchase_order()
            account_analytic_all = order.order_line.mapped("account_analytic_id")
            doc.account_analytic_all = account_analytic_all

    @api.depends("account_analytic_id")
    def _compute_fund_all(self):
        """Compute all fund on purchase order"""
        for doc in self:
            order = doc._get_purchase_order()
            fund_all = order.order_line.filtered(
                lambda l: l.account_analytic_id == self.account_analytic_id
            ).mapped("fund_id")
            doc.fund_all = fund_all

    @api.depends("account_analytic_id")
    def _compute_analytic_tag_all(self):
        """Compute all analytic on purchase order"""
        for doc in self:
            order = doc._get_purchase_order()
            analytic_tag_all = order.order_line.filtered(
                lambda l: l.account_analytic_id == self.account_analytic_id
            ).mapped("analytic_tag_ids")
            doc.analytic_tag_all = analytic_tag_all

    @api.onchange("fund_all")
    def _onchange_fund_all(self):
        for rec in self:
            rec.fund_id = rec.fund_all._origin.id if len(rec.fund_all) == 1 else False

    def _prepare_advance_purchase_line(self, order, product, tax_ids, amount):
        res = super()._prepare_advance_purchase_line(order, product, tax_ids, amount)
        res.update({"fund_id": self.fund_id.id})
        return res

    def _prepare_deposit_val(self, order, po_line, amount):
        res = super()._prepare_deposit_val(order, po_line, amount)
        res["invoice_line_ids"][0][2].update({"fund_id": po_line.fund_id.id})
        return res
