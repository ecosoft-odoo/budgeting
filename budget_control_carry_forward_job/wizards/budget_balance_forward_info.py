# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetBalanceForwardInfo(models.TransientModel):
    _inherit = "budget.balance.forward.info"

    def action_budget_balance_forward_job(self):
        self.ensure_one()
        self.forward_id.action_budget_balance_forward_job()
