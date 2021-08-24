# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _prepare_deduct_move_line(self, deduct):
        vals = super()._prepare_deduct_move_line(deduct)
        vals.update(
            {
                "activity_id": deduct.activity_id
                and deduct.activity_id.id
                or False
            }
        )
        return vals
