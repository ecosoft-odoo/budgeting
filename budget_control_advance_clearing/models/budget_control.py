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
        domain = [
            (
                "analytic_account_id",
                "in",
                self.mapped("analytic_account_id").ids,
            )
        ]
        budget_move = self.get_budget_move(doc_type="advance", domain=domain)
        advance_budget_move = budget_move["advance_budget_move"]
        if not advance_budget_move:
            self.write({"amount_advance": 0.0})
            return
        for rec in self:
            av_move = advance_budget_move.filtered(
                lambda l: l.analytic_account_id == rec.analytic_account_id
            )
            if not av_move:
                rec.amount_advance = 0.0
                continue
            amount_advance = sum(av_move.mapped("debit")) - sum(
                av_move.mapped("credit")
            )
            rec.amount_advance = amount_advance or 0.0

    def _get_amount_total_commit(self):
        amount_commit = (
            super()._get_amount_total_commit() + self.amount_advance
        )
        return amount_commit
