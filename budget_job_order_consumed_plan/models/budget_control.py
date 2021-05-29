# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    def _update_kpi_reset_plan(self, kpis):
        """
        Check budget move (Commitment) and Plan (Budget)
        if not plan, it will auto create new plan with commitment.
        """
        self.ensure_one()
        # NOT Update kpis, when you used Job Order
        super()._update_kpi_reset_plan(False)
        KPIxJO = self.env["budget.control.kpi.x.job.order"]
        KPI = self.env["mis.report.kpi"]
        domain = [("analytic_account_id", "=", self.analytic_account_id.id)]
        budget_move = self.get_move_commit(domain)
        kpi_x_job = self.kpi_x_job_order
        vals_kpixjob = []
        for move_obj in budget_move:
            for move in move_obj:
                # TODO: Test without contract
                if move._name == "contract.budget.move":
                    continue
                activity_group = move.activity_group_id.id
                job_order = move.job_order_id.id
                # There is Job Order in plan
                kpi_plan_job = kpi_x_job.filtered(
                    lambda l: l.job_order_ids.id == job_order
                )
                ag_kpi = KPI.search(
                    [("activity_group_id", "=", activity_group)]
                )
                if kpi_plan_job:
                    # There is Job Order, No AG in plan
                    kpi_no_ag = kpi_plan_job.filtered(
                        lambda l: activity_group
                        not in l.kpi_ids.mapped("activity_group_id").ids
                    )
                    if kpi_no_ag:  # Add in job
                        kpi_no_ag.kpi_ids = [(4, ag_kpi.id)]
                    continue
                # Case2: No Job Order in plan
                vals_kpixjob.append(
                    {
                        "budget_control_id": self.id,
                        "job_order_ids": job_order
                        and [(6, 0, [job_order])]
                        or False,
                        "kpi_ids": [(6, 0, ag_kpi.ids)],
                    }
                )
        if vals_kpixjob:
            KPIxJO.create(vals_kpixjob)

    def _context_filter_budget_info(self, item, date_to, all_kpi_ids):
        ctx = super()._context_filter_budget_info(item, date_to, all_kpi_ids)
        ctx["filter_job_order"] = item.job_order_id.id or [False]
        return ctx
