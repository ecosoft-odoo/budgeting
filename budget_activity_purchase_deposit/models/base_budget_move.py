# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetDoclineMixinBase(models.AbstractModel):
    _inherit = "budget.docline.mixin.base"

    def _domain_activity(self):
        """
        Filter out the activity deposit from the domain of the activity field,
        because the activity deposit is meant to be used only in the purchase deposit view.
        """
        domain = super()._domain_activity()
        activity_purchase_deposit = self.env.ref(
            "budget_activity_purchase_deposit.budget_activity_purchase_deposit"
        )
        if activity_purchase_deposit:
            domain.append(("id", "!=", activity_purchase_deposit.id))
        return domain
