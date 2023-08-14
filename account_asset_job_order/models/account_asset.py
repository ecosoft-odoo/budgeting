# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountAsset(models.Model):
    _inherit = "account.asset"

    filter_job_order = fields.Many2many(
        comodel_name="budget.job.order",
        compute="_compute_filter_job_order",
    )
    job_order_id = fields.Many2one(
        comodel_name="budget.job.order",
        string="Job Order",
        index=True,
        ondelete="restrict",
    )

    @api.onchange("filter_job_order")
    def _onchange_filter_job_order(self):
        """Reset job order when filter job has changed"""
        for rec in self:
            rec.job_order_id = False

    @api.depends("account_analytic_id")
    def _compute_filter_job_order(self):
        """Filter Job Order following Analytic Account.
        if job order is not analytic account, it mean global job order
        """
        JobOrder = self.env["budget.job.order"].search([])
        for rec in self:
            filter_job = JobOrder.filtered(
                lambda x: rec.account_analytic_id.id in x.analytic_account_ids.ids
                or not x.analytic_account_ids
            )
            rec.filter_job_order = filter_job
