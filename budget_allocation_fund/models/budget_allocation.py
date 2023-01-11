# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetAllocationLine(models.Model):
    _inherit = "budget.allocation.line"

    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        required=True,
        index=True,
        ondelete="restrict",
    )
    fund_group_id = fields.Many2one(
        comodel_name="budget.source.fund.group",
        related="fund_id.fund_group_id",
        store=True,
    )
