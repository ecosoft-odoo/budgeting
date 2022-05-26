# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class ContractLine(models.Model):
    _inherit = "contract.line"

    def _prepare_invoice_line(self, move_form):
        self.ensure_one()
        invoice_line_vals = super()._prepare_invoice_line(move_form)
        invoice_line_vals["fund_id"] = self.fund_id.id
        return invoice_line_vals
