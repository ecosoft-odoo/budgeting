# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetAllocationLine(models.Model):
    _inherit = "budget.allocation.line"

    transfered_amount = fields.Monetary(
        string="Transfered",
        default=0.0,
        help="Total transfered amount",
    )

    def _get_released_amount(self):
        res = super()._get_released_amount()
        return res + self.transfered_amount
