# Copyright 2020 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _create_payments(self):
        """Recompute advance budget, after payment reconciled"""
        payments = super()._create_payments()

        for payment in payments.filtered(lambda pay: pay.advance_id):
            ml_credit = payment.move_id.line_ids.filtered(lambda line: line.credit)
            advance_sheet = ml_credit.expense_id.sheet_id
            advance_sheet.recompute_budget_move()

        return payments
