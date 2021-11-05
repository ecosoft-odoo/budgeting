# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class MisBudgetItem(models.Model):
    _inherit = "mis.budget.item"

    activity_group_id = fields.Many2one(
        comodel_name="budget.activity.group",
        ondelete="cascade",
        index=True,
    )
