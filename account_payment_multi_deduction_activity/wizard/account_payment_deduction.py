# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class AccountPaymentDeduction(models.TransientModel):
    _inherit = "account.payment.deduction"

    activity_id = fields.Many2one(
        comodel_name="budget.activity",
    )

    @api.onchange("activity_id")
    def _onchange_activity_id(self):
        if self.activity_id:
            self.account_id = self.activity_id.account_id
