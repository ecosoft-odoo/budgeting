# Copyright 2022 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import api, models


class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    def _update_operating_unit_data(self, line_value, line_data):
        line_value.update(
            {
                "operating_unit_id": line_data.operating_unit_id.id,
            }
        )
        return line_value

    @api.model
    def _prepare_cash_basis_base_line_vals(
        self, base_line, balance, amount_currency
    ):
        res = super()._prepare_cash_basis_base_line_vals(
            base_line, balance, amount_currency
        )
        self._update_operating_unit_data(res, base_line)
        return res

    @api.model
    def _prepare_cash_basis_tax_line_vals(
        self, tax_line, balance, amount_currency
    ):
        res = super()._prepare_cash_basis_tax_line_vals(
            tax_line, balance, amount_currency
        )
        self._update_operating_unit_data(res, tax_line)
        return res

    @api.model
    def _prepare_cash_basis_counterpart_tax_line_vals(
        self, tax_line, cb_tax_line_vals
    ):
        res = super()._prepare_cash_basis_counterpart_tax_line_vals(
            tax_line, cb_tax_line_vals
        )
        self._update_operating_unit_data(res, tax_line)
        return res
