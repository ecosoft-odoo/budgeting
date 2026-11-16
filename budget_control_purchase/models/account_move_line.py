# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.exceptions import UserError
from odoo.tools import format_date

from odoo.addons.budget_control.models.analytic_plan import budget_row_key


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _related_analytic_distribution(self):
        """A purchase commitment carried forward is billed on the analytic
        distribution it was carried to."""
        vals = super()._related_analytic_distribution()
        purchase_line = self.purchase_line_id
        if purchase_line.fwd_analytic_distribution:
            vals = {
                key: percent
                for key, percent in vals.items()
                if key not in (purchase_line.analytic_distribution or {})
            } | purchase_line.fwd_analytic_distribution
        return vals

    def _get_po_line_amount_commit(self):
        """For hook, addition filter or condition i.e. purchase deposit"""
        self.ensure_one()
        return self.purchase_line_id.filtered("amount_commit")

    def _check_skip_negative_qty(self):
        """For hook, addition filter or condition i.e. purchase deposit"""
        self.ensure_one()
        return self.env.context.get("skip_negative_qty", False)

    def _get_qty_commit(self, purchase_line):
        """For hook, addition filter or condition i.e. purchase deposit"""
        qty = self.product_uom_id._compute_quantity(
            self.quantity, purchase_line.uom_id, round=False
        )
        qty_bf_invoice = purchase_line.qty_invoiced - qty
        qty_balance = purchase_line.product_qty - qty_bf_invoice
        qty = min(qty, qty_balance)
        return qty

    def uncommit_purchase_budget(self):
        """For vendor bill in valid state, do uncommit for related purchase."""
        for ml in self.filtered(
            lambda line: line.move_id.move_type in ("in_invoice", "in_refund")
        ):
            inv_state = ml.move_id.state
            move_type = ml.move_id.move_type
            # State Cancel or draft and not context force commit, not commitment line
            if not self.env.context.get("force_commit") and inv_state != "posted":
                self.env["purchase.budget.move"].sudo().search(
                    [("move_line_id", "=", ml.id)]
                ).unlink()
                continue
            # Vendor bills and purchase order must be related
            # and po must commit budget already
            purchase_line = ml._get_po_line_amount_commit()
            if not purchase_line:
                continue
            # Vendor bills must be qty > 0
            qty = ml._get_qty_commit(purchase_line)
            if qty <= 0 and not ml._check_skip_negative_qty():
                continue

            # The rows of the bill line must be those of the purchase
            # commitment at its date, e.g. the rows a forward carried it to
            def row(key):
                return budget_row_key(int(aid) for aid in str(key).split(","))

            purchase_rows = purchase_line._get_budget_rows_at(
                ml.date_commit or ml.move_id.date
            )
            if any(
                row(key) not in purchase_rows for key in ml.analytic_distribution or {}
            ):
                raise UserError(
                    self.env._(
                        "Analytic distribution mismatch. "
                        "Please align with the original purchase order."
                    )
                )

            # Only case reverse and want to return_amount_commit
            context = {}
            if move_type == "in_invoice" and ml.return_amount_commit:
                context["return_amount_commit"] = ml.amount_commit
            # Confirm vendor bill, do uncommit budget
            context["product_qty"] = qty
            purchase_line.with_context(**context).commit_budget(
                reverse=move_type == "in_invoice",
                analytic_distribution=ml.analytic_distribution,
                move_line_id=ml.id,
                date=ml.date_commit,
            )

    def _check_purchase_forward_date(self):
        """A purchase commitment carried forward is billed from the forward
        date: an earlier bill would return a commitment no longer there."""
        for ml in self.filtered("purchase_line_id"):
            forward_date = ml.purchase_line_id._get_budget_forward_date()
            if forward_date and (ml.date_commit or ml.move_id.date) < forward_date:
                raise UserError(
                    self.env._(
                        "%(purchase)s is carried forward to %(date)s: date its bills "
                        "from then, or reverse the forward.",
                        purchase=ml.purchase_line_id.order_id.display_name,
                        date=format_date(self.env, forward_date),
                    )
                )
