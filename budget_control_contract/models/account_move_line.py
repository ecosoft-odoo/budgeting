# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def uncommit_contract_budget(self):
        """For vendor bill in valid state, do uncommit for related contract."""
        for ml in self:
            inv_state = ml.move_id.state
            move_type = ml.move_id.move_type
            if move_type in ("in_invoice", "in_refund"):
                if inv_state == "posted":
                    rev = move_type == "in_invoice" and True or False
                    contract_line = ml.contract_line_id.filtered(
                        "amount_commit"
                    )
                    if not contract_line:
                        continue
                    contract_line.commit_budget(
                        reverse=rev, move_line_id=ml.id
                    )
                else:  # Cancel or draft, not commitment line
                    self.env["contract.budget.move"].search(
                        [("move_line_id", "=", ml.id)]
                    ).unlink()
