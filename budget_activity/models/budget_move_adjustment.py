# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BudgetMoveAdjustmentItem(models.Model):
    _inherit = "budget.move.adjustment.item"

    activity_id = fields.Many2one(
        comodel_name="budget.activity",
        string="Activity",
        index=True,
    )

    _sql_constraints = [
        (
            "amount_positive",
            "CHECK(amount >= 0)",
            "The adjusted budget must be positive.",
        )
    ]

    @api.onchange("activity_id")
    def _onchange_activity_id(self):
        if self.activity_id:
            self.account_id = self.activity_id.account_id
