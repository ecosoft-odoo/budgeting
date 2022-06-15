# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class BudgetDoclineMixinBase(models.AbstractModel):
    _inherit = "budget.docline.mixin.base"

    def _domain_activity(self):
        domain = super()._domain_activity()
        advance = self.env.ref("budget_activity_advance_clearing.activity_advance")
        advance and domain.append(("id", "!=", advance.id)) or domain
        return domain
