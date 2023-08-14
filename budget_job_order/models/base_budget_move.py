# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BaseBudgetMove(models.AbstractModel):
    _inherit = "base.budget.move"

    job_order_id = fields.Many2one(
        comodel_name="budget.job.order",
        string="Job Order",
        index=True,
        ondelete="restrict",
    )


class BudgetDoclineMixinBase(models.AbstractModel):
    _inherit = "budget.docline.mixin.base"

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

    @api.depends(
        lambda self: (self._budget_analytic_field,)
        if self._budget_analytic_field
        else ()
    )
    def _compute_filter_job_order(self):
        """Filter Job Order following Analytic Account.
        if job order is not analytic account, it mean global job order
        """
        JobOrder = self.env["budget.job.order"].search([])
        for doc in self:
            filter_job = JobOrder.filtered(
                lambda x: doc[doc._budget_analytic_field].id
                in x.analytic_account_ids.ids
                or not x.analytic_account_ids
            )
            doc.filter_job_order = filter_job


class BudgetDoclineMixin(models.AbstractModel):
    _inherit = "budget.docline.mixin"

    def _update_budget_commitment(self, budget_vals, reverse=False):
        budget_vals = super()._update_budget_commitment(budget_vals, reverse=reverse)
        budget_vals["job_order_id"] = self.job_order_id.id
        return budget_vals
