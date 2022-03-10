# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class BudgetDoclineMixinBase(models.AbstractModel):
    _inherit = "budget.docline.mixin.base"

    def _domain_activity(self):
        domain = super()._domain_activity()
        activity_purchase_deposit = self.env.ref(
            "budget_activity_purchase_deposit.activity_purchase_deposit"
        )
        activity_purchase_deposit and domain.append(
            ("id", "!=", activity_purchase_deposit.id)
        ) or domain
        return domain
