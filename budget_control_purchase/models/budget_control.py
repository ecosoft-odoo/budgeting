# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    amount_purchase = fields.Monetary(
        string="Purchase",
        compute="_compute_amount_purchase",
        help="Sum of purchase amount",
    )

    @api.depends("item_ids")
    def _compute_amount_purchase(self):
        PurchaseBudgetMove = self.env["purchase.budget.move"]
        for rec in self:
            po_move = PurchaseBudgetMove.search(
                [("analytic_account_id", "=", rec.analytic_account_id.id)]
            )
            amount_purchase = sum(po_move.mapped("debit")) - sum(
                po_move.mapped("credit")
            )
            rec.amount_purchase = amount_purchase or 0.0

    def _get_amount_total_commit(self):
        amount_commit = (
            super()._get_amount_total_commit() + self.amount_purchase
        )
        return amount_commit
