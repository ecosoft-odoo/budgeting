# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    purchase_budget_actual_source = fields.Selection(
        related="purchase_line_id.budget_actual_source",
        string="Purchase Budget Actual Source",
        store=True,
        readonly=True,
    )

    @api.depends(
        "move_id.not_affect_budget",
        "not_affect_budget",
        "analytic_distribution",
        "purchase_budget_actual_source",
    )
    def _compute_can_commit(self):
        res = super()._compute_can_commit()
        stock_actual_lines = self.filtered(
            lambda line: line.purchase_budget_actual_source == "stock_issue"
            and line.move_id.move_type in ("in_invoice", "in_refund")
        )
        stock_actual_lines.update({"can_commit": False})
        return res

    def _get_po_line_amount_commit(self):
        """A stock-issued purchase stays committed until the outgoing move."""
        purchase_line = super()._get_po_line_amount_commit()
        return purchase_line.filtered(
            lambda line: line.budget_actual_source != "stock_issue"
        )

    def _get_qty_commit(self, purchase_line):
        """Cap uncommit qty by remaining PO commitment in the PO UoM.

        When part of a PO has already been uncommitted via DO lot tracing,
        the vendor bill must not over-uncommit the remaining balance.
        """
        qty = super()._get_qty_commit(purchase_line)
        remaining_qty = purchase_line._get_remaining_budget_commit_qty()
        return min(qty, remaining_qty)
