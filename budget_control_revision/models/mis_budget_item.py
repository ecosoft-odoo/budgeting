# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class MisBudgetItem(models.Model):
    _inherit = "mis.budget.item"

    def _prepare_overlap_domain(self):
        domain = super()._prepare_overlap_domain()
        domain.extend([("budget_control_id", "=", self.budget_control_id.id)])
        return domain
