# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetPlan(models.Model):
    _inherit = "budget.plan"

    def action_generate_plan(self):
        res = super().action_generate_plan()
        self.ensure_one()
        for line in self.plan_line:
            fund_amount = line.analytic_account_id.fund_constraint_ids.mapped(
                "fund_amount"
            )
            line.amount = sum(fund_amount)
        return res
