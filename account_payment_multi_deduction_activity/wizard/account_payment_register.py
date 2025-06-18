# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    activity_id = fields.Many2one(
        comodel_name="budget.activity",
    )

    @api.onchange("activity_id")
    def _onchange_activity_id(self):
        if self.activity_id:
            self.writeoff_account_id = self.activity_id.account_id

    def _prepare_deduct_move_line(self, deduct):
        # Multi Deduction
        vals = super()._prepare_deduct_move_line(deduct)
        vals.update(
            {"activity_id": deduct.activity_id and deduct.activity_id.id or False}
        )
        return vals

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        # Payment Difference
        if self.payment_difference_handling == "reconcile" and payment_vals.get(
            "write_off_line_vals", []
        ):
            payment_vals["write_off_line_vals"][0].update(
                {
                    "activity_id": self.activity_id.id,
                }
            )
        return payment_vals
