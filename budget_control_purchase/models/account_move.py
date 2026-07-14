# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def write(self, vals):
        """Uncommit budget for source purchase document."""
        res = super().write(vals)
        if vals.get("state") in ("draft", "posted", "cancel"):
            # The PO commitment already exists.  Rebuilding every source PO line
            # here used to unlink it, create it again, and only then create the
            # invoice reversal.  Update only the reversal owned by these invoice
            # lines; draft/cancel removes it and posted creates it.
            invoice_lines = self.mapped("invoice_line_ids").filtered("purchase_line_id")
            invoice_lines.uncommit_purchase_budget()
            # Budget totals are non-stored SQL aggregates and their declared
            # dependency is the budget plan lines.  Incremental PO reversals do
            # not touch those lines, so explicitly drop any totals cached earlier
            # in the transaction (the old full PO rebuild did this incidentally).
            BudgetControl = self.env["budget.control"]
            budget_info_fields = [
                name
                for name, field in BudgetControl._fields.items()
                if field.compute == "_compute_budget_info"
            ]
            BudgetControl.invalidate_model(budget_info_fields)
        return res
