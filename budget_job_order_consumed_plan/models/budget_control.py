# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    def _update_kpi_reset_plan(self, kpis):
        self.ensure_one()
        super()._update_kpi_reset_plan(kpis)
        KPIxJO = self.env["budget.control.kpi.x.job.order"]
        domain = [
            ("analytic_account_id", "=", self.analytic_account_id.id),
            ("job_order_id", "!=", False),
        ]
        budget_move = self.get_move_commit(domain)
        # Same AG, Difference Job
        for move_obj in budget_move:
            for move in move_obj:
                activity_group = move.activity_group_id.id
                job_order = move.job_order_id.id
                kpi_jo = self.kpi_x_job_order.filtered(
                    lambda l: l.kpi_ids.activity_group_id.id == activity_group
                    and job_order not in l.job_order_ids.ids
                )
                if kpi_jo:
                    kpi_jo.job_order_ids = [(4, job_order)]
        # New AG with job order
        for kpi in list(set(kpis)):
            move_job = [
                move_obj.filtered(
                    lambda l: l.activity_group_id == kpi.activity_group_id
                )
                for move_obj in budget_move
            ]
            self.kpi_x_job_order += KPIxJO.new(
                {
                    "kpi_ids": [kpi.id],
                    "job_order_ids": [
                        (4, x.job_order_id.id) for x in move_job
                    ],
                }
            )

    def _context_filter_budget_info(self, item, date_to):
        ctx = super()._context_filter_budget_info(item, date_to)
        ctx["filter_job_order"] = item.job_order_id.id or [False]
        return ctx
