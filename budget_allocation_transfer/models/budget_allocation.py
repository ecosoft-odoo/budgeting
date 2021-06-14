# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetAllocationLine(models.Model):
    _inherit = "budget.allocation.line"

    transferred_amount = fields.Monetary(
        string="Transferred",
        default=0.0,
        help="Total transferred amount",
    )

    def _get_released_amount(self):
        res = super()._get_released_amount()
        return res + self.transferred_amount
