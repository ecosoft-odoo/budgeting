# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        """ Check Fund Constraint per move line """
        res = super().action_post()
        FundConstraint = self.env["fund.constraint"]
        for move in self:
            for aml in move.line_ids.filtered("fund_id"):
                domain = [
                    ("analytic_account_id", "=", aml.analytic_account_id.id),
                    ("fund_id", "=", aml.fund_id.id),
                ]
                fund_constraint_ids = FundConstraint.search(domain)
                balance = abs(aml.balance)
                fund_over_limit = fund_constraint_ids.filtered(
                    lambda l: l.fund_amount < balance
                )
                for fc in fund_over_limit:
                    over_limit = balance - fc.fund_amount
                    raise UserError(
                        _(
                            "{} spent fund amount over limit {:,.2f} {}".format(
                                aml.name, over_limit, fc.currency_id.symbol
                            )
                        )
                    )
        return res
