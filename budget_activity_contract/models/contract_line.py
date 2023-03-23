# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class ContractLine(models.Model):
    _inherit = "contract.line"

    def _prepare_invoice_line(self, move_form):
        self.ensure_one()
        invoice_line_vals = super()._prepare_invoice_line(move_form)
        if self.activity_id and invoice_line_vals:
            invoice_line_vals["activity_id"] = self.activity_id.id
            invoice_line_vals["account_id"] = self.activity_id.account_id.id
        return invoice_line_vals

    def _get_contract_line_account(self):
        account = super()._get_contract_line_account()
        if self.activity_id:
            account = self.activity_id.account_id
        return account
