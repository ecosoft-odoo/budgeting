# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class PurchaseAdvancePaymentInv(models.TransientModel):
    _inherit = "purchase.advance.payment.inv"

    account_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Analytic Account",
    )
    account_analytic_all = fields.Many2many(
        comodel_name="account.analytic.account",
        compute="_compute_account_analytic_all",
        compute_sudo=True,
    )
    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        domain="[('id', 'in', fund_all)]",
    )
    fund_all = fields.Many2many(
        comodel_name="budget.source.fund",
        compute="_compute_fund_all",
        compute_sudo=True,
    )
    analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        string="Analytic Tags",
    )
    analytic_tag_all = fields.Many2many(
        comodel_name="account.analytic.tag",
        compute="_compute_analytic_tag_all",
        compute_sudo=True,
    )

    def _get_purchase_order(self):
        """
        Get purchase order
        """
        order = False
        active_id = self._context.get("active_id")
        active_model = self._context.get("active_model")
        if active_model == "purchase.order":
            order = self.env[active_model].browse(active_id)
        return order

    def _compute_account_analytic_all(self):
        """
        Compute all analytic account on purchase order
        """
        for doc in self:
            order = doc._get_purchase_order()
            account_analytic_all = []
            if order:
                account_analytic_all = order.order_line.mapped(
                    "account_analytic_id"
                )
            doc.account_analytic_all = account_analytic_all

    @api.depends("account_analytic_id")
    def _compute_fund_all(self):
        """
        Compute all fund on purchase order
        """
        for doc in self:
            order = doc._get_purchase_order()
            fund_all = []
            if order:
                fund_all = order.order_line.filtered(
                    lambda l: l.account_analytic_id == self.account_analytic_id
                ).mapped("fund_id")
            doc.fund_all = fund_all

    @api.depends("account_analytic_id")
    def _compute_analytic_tag_all(self):
        """
        Compute all analytic on purchase order
        """
        for doc in self:
            order = doc._get_purchase_order()
            analytic_tag_all = []
            if order:
                analytic_tag_all = order.order_line.filtered(
                    lambda l: l.account_analytic_id == self.account_analytic_id
                ).mapped("analytic_tag_ids")
            doc.analytic_tag_all = analytic_tag_all

    @api.model
    def default_get(self, field_list):
        """
        Default aa, fund, aa tag
        """
        res = super().default_get(field_list)
        order = self._get_purchase_order()
        if order and order.order_line:
            order_line = order.order_line
            account_analytics = order_line.mapped("account_analytic_id")
            if len(account_analytics) == 1:
                res.update({"account_analytic_id": account_analytics.id})
            funds = order_line.mapped("fund_id")
            if len(funds) == 1:
                res.update({"fund_id": funds.id})
            analytic_tags = order_line.mapped("analytic_tag_ids")
            if analytic_tags == order_line[0].analytic_tag_ids:
                res.update({"analytic_tag_ids": analytic_tags.ids})
        return res

    def _prepare_advance_purchase_line(self, order, product, tax_ids, amount):
        res = super()._prepare_advance_purchase_line(
            order, product, tax_ids, amount
        )
        res.update(
            {
                "account_analytic_id": self.account_analytic_id.id,
                "fund_id": self.fund_id.id,
                "analytic_tag_ids": [(6, 0, self.analytic_tag_ids.ids)],
            }
        )
        return res

    def _prepare_deposit_val(self, order, po_line, amount):
        res = super()._prepare_deposit_val(order, po_line, amount)
        res["invoice_line_ids"][0][2].update(
            {
                "analytic_tag_ids": [(6, 0, po_line.analytic_tag_ids.ids)],
                "fund_id": po_line.fund_id.id,
            }
        )
        return res
