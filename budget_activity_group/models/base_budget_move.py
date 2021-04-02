# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BaseBudgetMove(models.AbstractModel):
    _inherit = "base.budget.move"

    activity_group_id = fields.Many2one(
        comodel_name="budget.activity.group",
        string="Activity Group",
        related="activity_id.activity_group_id",
    )
