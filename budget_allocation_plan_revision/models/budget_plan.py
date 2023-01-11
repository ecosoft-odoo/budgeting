# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ast

from odoo import models


class BudgetPlan(models.Model):
    _inherit = "budget.plan"

    def create_revision(self):
        res = super().create_revision()
        new_plan = self.search(ast.literal_eval(res.get("domain", False)))
        new_plan.ensure_one()
        new_plan.budget_allocation_id.write({"plan_id": new_plan.id})
        return res
