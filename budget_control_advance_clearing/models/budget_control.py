# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    amount_advance = fields.Monetary(
        string="Advance",
        compute="_compute_amount_advance",
        help="Sum of expense amount",
    )

    @api.depends("item_ids")
    def _compute_amount_advance(self):
        ExpenseBudgetMove = self.env["advance.budget.move"]
        for rec in self:
            av_move = ExpenseBudgetMove.search(
                [("analytic_account_id", "=", rec.analytic_account_id.id)]
            )
            amount_advance = sum(av_move.mapped("debit")) - sum(
                av_move.mapped("credit")
            )
            rec.amount_advance = amount_advance or 0.0

    def _get_amount_total_commit(self):
        amount_commit = (
            super()._get_amount_total_commit() + self.amount_advance
        )
        return amount_commit
