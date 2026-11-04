# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends("activity_id")
    def _compute_account_id(self):
        """Activity's account takes priority over product's account, except
        on purchases that Odoo books on the stock valuation account of their
        product (real-time valuation)."""
        res = super()._compute_account_id()
        for line in self.filtered("activity_id.account_id"):
            if not line._is_stock_valuation_line():
                line.account_id = line.activity_id.account_id
        return res

    def _is_stock_valuation_line(self):
        """Whether Odoo books this line on the stock valuation account of its
        product, as ``_compute_account_id()`` does."""
        self.ensure_one()
        if not (
            self.display_type == "product"
            and self.product_id
            and self.move_id.is_purchase_document(include_receipts=True)
            and self._use_inventory_valuation()
        ):
            return False
        accounts = self.with_company(
            self.company_id
        ).product_id.product_tmpl_id.get_product_accounts(
            fiscal_pos=self.move_id.fiscal_position_id
        )
        return bool(accounts["stock_valuation"])

    def _prepare_analytic_lines(self):
        """Add activity_id to analytic line"""
        analytic_line_vals = super()._prepare_analytic_lines()
        if self.activity_id:
            for analytic_line in analytic_line_vals:
                analytic_line["activity_id"] = self.activity_id.id
        return analytic_line_vals
