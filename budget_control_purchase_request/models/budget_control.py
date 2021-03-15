# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    amount_purchase_request = fields.Monetary(
        string="Purchase Request",
        compute="_compute_amount_purchase_request",
        help="Sum of purchase amount",
    )

    @api.depends("item_ids")
    def _compute_amount_purchase_request(self):
        domain = [
            (
                "analytic_account_id",
                "in",
                self.mapped("analytic_account_id").ids,
            )
        ]
        budget_move = self.get_budget_move(
            doc_type="purchase_request", domain=domain
        )
        purchase_request_budget_move = budget_move[
            "purchase_request_budget_move"
        ]
        if not purchase_request_budget_move:
            self.write({"amount_purchase_request": 0.0})
            return
        for rec in self:
            pr_move = purchase_request_budget_move.filtered(
                lambda l: l.analytic_account_id == rec.analytic_account_id
            )
            if not pr_move:
                rec.amount_purchase_request = 0.0
                continue
            amount_purchase_request = sum(pr_move.mapped("debit")) - sum(
                pr_move.mapped("credit")
            )
            rec.amount_purchase_request = amount_purchase_request or 0.0

    def _get_amount_total_commit(self):
        amount_commit = (
            super()._get_amount_total_commit() + self.amount_purchase_request
        )
        return amount_commit
