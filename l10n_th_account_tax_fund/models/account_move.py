# Copyright 2022 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange("invoice_line_ids")
    def _onchange_invoice_line_ids(self):
        res = super()._onchange_invoice_line_ids()
        for move in self:
            fund_ids = move.invoice_line_ids.mapped("fund_id")
            if len(fund_ids) == 1:
                for line in self.line_ids:
                    if not line.fund_id:
                        line.fund_id = fund_ids
        return res
