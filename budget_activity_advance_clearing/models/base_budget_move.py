# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetDoclineMixinBase(models.AbstractModel):
    _inherit = "budget.docline.mixin.base"

    def _domain_activity(self):
        """
        Filter out the activity advance from the domain of the activity field,
        because the activity advance is meant to be used only in the advances view.
        """
        domain = super()._domain_activity()
        advance_activity = self.env.ref(
            "budget_activity_advance_clearing.budget_activity_advance"
        )
        if advance_activity:
            domain.append(("id", "!=", advance_activity.id))
        return domain
