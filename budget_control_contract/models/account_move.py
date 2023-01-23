# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def write(self, vals):
        """Uncommit budget for source contract document."""
        res = super().write(vals)
        if vals.get("state") in ("draft", "posted", "cancel"):
            contract_lines = self.mapped("invoice_line_ids.contract_line_id")
            contract_lines.recompute_budget_move()
        return res
