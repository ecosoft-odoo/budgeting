# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetCommitForwardInfo(models.TransientModel):
    _inherit = "budget.commit.forward.info"

    def action_budget_commit_forward_job(self):
        self.ensure_one()
        self.forward_id.action_budget_commit_forward_job()
