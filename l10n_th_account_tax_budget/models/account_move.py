# Copyright 2022 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange("invoice_line_ids")
    def _onchange_invoice_line_ids(self):
        res = super()._onchange_invoice_line_ids()
        for move in self:
            analytic_account_ids = move.invoice_line_ids.mapped(
                "analytic_account_id"
            )
            if len(analytic_account_ids) == 1:
                tag_lines = move.invoice_line_ids.filtered(
                    lambda l: l.analytic_account_id and l.analytic_tag_ids
                )
                for line in self.line_ids:
                    line.analytic_account_id = analytic_account_ids
                    if not line.analytic_tag_ids and tag_lines:
                        line.analytic_tag_ids = tag_lines[0].analytic_tag_ids
        return res
