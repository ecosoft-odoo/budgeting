# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "budget.docline.mixin"]
    _doc_date_fields = ["move_id.date"]

    budget_move_ids = fields.One2many(
        comodel_name="account.budget.move",
        inverse_name="move_line_id",
        string="Account Budget Moves",
    )

    def recompute_budget_move(self):
        for invoice_line in self:
            invoice_line.budget_move_ids.unlink()
            # Commit on invoice
            invoice_line.commit_budget()

    def _check_amount_currency_tax(self, date, doc_type="account"):
        self.ensure_one()
        budget_period = self.env["budget.period"]._get_eligible_budget_period(
            date, doc_type
        )
        amount_currency = (
            budget_period.include_tax
            and max(self.amount_currency, self.price_total)
            or self.amount_currency
        )
        return amount_currency

    def commit_budget(self, reverse=False):
        """Create budget commit for each move line."""
        self.ensure_one()
        if (
            self.can_commit()
            and self.move_id.state == "posted"
            and not self.move_id.not_affect_budget
        ):
            account = self.account_id
            analytic_account = self.analytic_account_id
            amount_currency = self._check_amount_currency_tax(self.date_commit)
            currency = self.currency_id
            vals = self._prepare_budget_commitment(
                account,
                analytic_account,
                self.date_commit,
                amount_currency,
                currency,
                reverse=reverse,
            )
            # Document specific vals
            vals.update(
                {
                    "move_line_id": self.id,
                    "analytic_tag_ids": [(6, 0, self.analytic_tag_ids.ids)],
                }
            )
            budget_move = self.env["account.budget.move"].create(vals)
            if reverse:  # On reverse, make sure not over returned
                self.env["budget.period"].check_over_returned_budget(
                    self.move_id
                )
            return budget_move
        else:
            self.budget_move_ids.unlink()
