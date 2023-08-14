# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import itertools
import operator

from odoo import models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    def _get_kpis(self):
        """Overwrite get kpi from kpi_x_job_order"""
        return self.kpi_x_job_order.mapped("kpi_ids")

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
                activity_group = move.activity_group_id.id
                job_order = move.job_order_id.id
                # There is Job Order in plan
                kpi_plan_job = kpi_x_job.filtered(
                    lambda x: x.job_order_ids.id == job_order
                )
                ag_kpi = KPI.search([("activity_group_id", "=", activity_group)])
                if kpi_plan_job:
                    # There is Job Order, No AG in plan
                    kpi_no_ag = kpi_plan_job.filtered(
                        lambda x: activity_group
                        not in x.kpi_ids.mapped("activity_group_id").ids
                    )
                    if kpi_no_ag:  # Add in job
                        kpi_no_ag.kpi_ids = [(4, ag_kpi.id)]
                    continue
                # Case2: No Job Order in plan, Add job order and kpi
                dict_new_kpi = {
                    "job_order_id": job_order or False,
                    "kpi_ids": ag_kpi.id,
                }
                if dict_new_kpi not in vals_kpixjob:
                    vals_kpixjob.append(dict_new_kpi)
        if vals_kpixjob:
            budget_control_id = self.id
            key = operator.itemgetter("job_order_id")
            # Combine new job order duplicate into 1, sorted by value to False
            combine_vals = [
                {"job_order_id": x, "kpi_ids": [d["kpi_ids"] for d in y]}
                for x, y in itertools.groupby(
                    sorted(vals_kpixjob, key=key, reverse=True), key=key
                )
            ]
            # Add value for create new line KPIs
            vals_newkpi = list(
                map(
                    lambda x: {
                        "budget_control_id": budget_control_id,
                        "job_order_ids": x["job_order_id"]
                        and [(6, 0, [x["job_order_id"]])]
                        or False,
                        "kpi_ids": [(6, 0, x["kpi_ids"])],
                    },
                    combine_vals,
                )
            )
            KPIxJO.create(vals_newkpi)

    def _context_filter_budget_info(self, item, date_to, all_kpi_ids):
        ctx = super()._context_filter_budget_info(item, date_to, all_kpi_ids)
        ctx["filter_job_order"] = item.job_order_id.id or [False]
        return ctx
