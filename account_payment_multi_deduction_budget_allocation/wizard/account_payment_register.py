# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import models


class AccountPaymentRegister(models.TransientModel):
    _name = "account.payment.register"
    _inherit = [
        "analytic.dimension.line",
        "account.payment.register",
        "budget.docline.mixin.base",
    ]
    _budget_analytic_field = "writeoff_analytic_account_id"
    _analytic_tag_field_name = "writeoff_analytic_tag_ids"

    def _prepare_deduct_move_line(self, deduct):
        vals = super()._prepare_deduct_move_line(deduct)
        vals.update({"fund_id": deduct.fund_id and deduct.fund_id.id or False})
        return vals

    def _create_payment_vals_from_wizard(self):
        payment_vals = super()._create_payment_vals_from_wizard()
        if (
            not self.currency_id.is_zero(self.payment_difference)
            and self.payment_difference_handling == "reconcile"
        ):
            payment_vals["write_off_line_vals"]["fund_id"] = self.fund_id.id
        return payment_vals

    def _update_vals_deduction(self, moves):
        res = super()._update_vals_deduction(moves)
        self._onchange_fund_all()
        return res
