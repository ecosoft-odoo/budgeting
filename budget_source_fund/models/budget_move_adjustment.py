# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetMoveAdjustmentItem(models.Model):
    _inherit = "budget.move.adjustment.item"

    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        string="Fund",
        domain=[],  # clear domain
        index=True,
    )
