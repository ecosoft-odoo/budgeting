# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange("purchase_vendor_bill_id", "purchase_id")
    def _onchange_purchase_auto_complete(self):
        """After loading PO lines, mark not_affect_budget on lines whose
        PO line analytic is configured as stock_done.
        """
        res = super()._onchange_purchase_auto_complete()
        self._compute_not_affect_budget_from_po()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """For bills created with PO lines (e.g., import), apply the
        not_affect_budget flag based on PO line analytics.
        """
        moves = super().create(vals_list)
        for move in moves:
            if move.move_type in ("in_invoice", "in_refund"):
                move._compute_not_affect_budget_from_po()
        return moves

    def write(self, vals):
        """If PO lines or invoice lines change, re-evaluate not_affect_budget."""
        res = super().write(vals)
        if "line_ids" in vals and self.move_type in ("in_invoice", "in_refund"):
            self._compute_not_affect_budget_from_po()
        return res

    @api.constrains("line_ids", "not_affect_budget")
    def _check_not_affect_budget_cascade(self):
        """Cascade: if all real lines have not_affect_budget=True,
        auto-set header to True.
        """
        for move in self:
            if move.move_type not in ("in_invoice", "in_refund"):
                continue

            real_lines = move.line_ids.filtered(
                lambda line: line.display_type == "product"
            )
            if not real_lines:
                continue

            if all(line.not_affect_budget for line in real_lines):
                if not move.not_affect_budget:
                    move.not_affect_budget = True

    def _compute_not_affect_budget_from_po(self):
        """For vendor bills with PO lines: if any PO line analytic is
        configured as stock_done, set not_affect_budget=True on the
        matching bill line(s). Manual bills (no PO) are not touched.
        """
        self.ensure_one()
        if self.move_type not in ("in_invoice", "in_refund"):
            return
        if not self.invoice_line_ids:
            return
        # Manual bills: no purchase_line_id on any line
        po_lines = self.invoice_line_ids.mapped("purchase_line_id")
        if not po_lines:
            return
        # For each bill line with a PO line, check PO line analytics
        for inv_line in self.invoice_line_ids.filtered("purchase_line_id"):
            pol = inv_line.purchase_line_id
            is_stock_done = self._is_po_analytic_stock_done(pol)
            if is_stock_done:
                inv_line.not_affect_budget = True
            else:
                # Reset if previously flagged (e.g., analytic changed)
                if inv_line.not_affect_budget:
                    inv_line.not_affect_budget = False
        # Trigger cascade check
        self._check_not_affect_budget_cascade()

    def _is_po_analytic_stock_done(self, purchase_line):
        """Return True if any analytic on the PO line has stock_done
        as its effective budget actual source.
        """
        distribution = purchase_line.analytic_distribution
        if not distribution:
            return False
        AnalyticAccount = self.env["account.analytic.account"]
        for key in distribution:
            for analytic_id_str in key.split(","):
                analytic = AnalyticAccount.browse(int(analytic_id_str.strip()))
                if not analytic:
                    continue
                if analytic._get_effective_budget_actual_source() == "stock_done":
                    return True
        return False
