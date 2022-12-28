# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    def _get_context_budget_monitoring(self):
        ctx = super()._get_context_budget_monitoring()
        ctx.update({"search_default_group_by_activity_group": 1})
        return ctx
