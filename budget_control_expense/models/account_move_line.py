# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def uncommit_expense_budget(self):
        """For vendor bill in valid state, do uncommit for related expense."""
        for ml in self:
            inv_state = ml.move_id.state
            move_type = ml.move_id.move_type
            if move_type in ("entry"):
                if inv_state == "posted":
                    expense = ml.expense_id
                    # Because this is not invoice, we need to compare account
                    if not expense or ml.account_id != expense.account_id:
                        continue
                    expense.commit_budget(reverse=True, move_line_id=ml.id)
                else:  # Cancel or draft, not commitment line
                    self.env["expense.budget.move"].search(
                        [("move_line_id", "=", ml.id)]
                    ).unlink()

    def _check_amount_currency_tax(self, date, doc_type="account"):
        self.ensure_one()
        amount_currency = super()._check_amount_currency_tax(date, doc_type)
        if self.expense_id:
            budget_period = self.env[
                "budget.period"
            ]._get_eligible_budget_period(date, doc_type=doc_type)
            price = self._get_price_total_and_subtotal_model(
                self.amount_currency,
                self.quantity,
                self.discount,
                self.currency_id,
                self.product_id,
                self.partner_id,
                self.tax_ids,
                "entry",
            )
            amount_currency = (
                budget_period.include_tax
                and price.get("price_total", 0.0)
                or self.amount_currency
            )
        return amount_currency
