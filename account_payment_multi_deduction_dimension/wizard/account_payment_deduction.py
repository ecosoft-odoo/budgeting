# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import models


class AccountPaymentDeduction(models.TransientModel):
    _name = "account.payment.deduction"
    _inherit = [
        "analytic.dimension.line",
        "account.payment.deduction",
    ]
    _analytic_tag_field_name = "analytic_tag_ids"
