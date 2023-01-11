# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import models


class AccountPaymentRegister(models.TransientModel):
    _name = "account.payment.register"
    _inherit = [
        "analytic.dimension.line",
        "account.payment.register",
    ]
    _analytic_tag_field_name = "writeoff_analytic_tag_ids"
