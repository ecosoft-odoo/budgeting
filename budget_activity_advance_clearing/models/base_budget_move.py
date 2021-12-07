# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetDoclineMixinBase(models.AbstractModel):
    _inherit = "budget.docline.mixin.base"

    activity_id = fields.Many2one(
        comodel_name="budget.activity",
        domain=lambda self: [
            (
                "id",
                "!=",
                self.env.ref(
                    "budget_activity_advance_clearing.activity_advance", 0
                ).id,
            )
        ],
    )
