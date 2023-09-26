# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetBalanceForward(models.Model):
    _inherit = "budget.balance.forward"

    job_uuid = fields.Char(
        string="Job UUID",
        readonly=True,
    )

    def action_budget_balance_forward_job(self):
        description = _("Creating forward balance budget with id %s") % (
            self.id,
        )
        job = self.with_delay(description=description).action_budget_balance_forward()
        # Update UUID in forward commit
        self.job_uuid = job.uuid
        return "Job created with uuid {}".format(job.uuid)
