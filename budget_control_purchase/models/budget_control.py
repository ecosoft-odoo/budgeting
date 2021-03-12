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
        domain = [
            (
                "analytic_account_id",
                "in",
                self.mapped("analytic_account_id").ids,
            )
        ]
        budget_move = self.get_budget_move(doc_type="purchase", domain=domain)
        purchase_budget_move = budget_move["purchase_budget_move"]
        if not purchase_budget_move:
            self.write({"amount_purchase": 0.0})
            return
        for rec in self:
            po_move = purchase_budget_move.filtered(
                lambda l: l.analytic_account_id == rec.analytic_account_id
            )
            if not po_move:
                rec.amount_purchase = 0.0
                continue
            amount_purchase = sum(po_move.mapped("debit")) - sum(
                po_move.mapped("credit")
            )
            rec.amount_purchase = amount_purchase or 0.0

    def _get_amount_total_commit(self):
        amount_commit = (
            super()._get_amount_total_commit() + self.amount_purchase
        )
        return amount_commit
