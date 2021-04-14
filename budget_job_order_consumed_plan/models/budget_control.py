# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    def _update_kpi_reset_plan(self, kpis):
        self.ensure_one()
        super()._update_kpi_reset_plan(kpis)
        KPIxJO = self.env["budget.control.kpi.x.job.order"]
        for kpi in list(set(kpis)):
            self.kpi_x_job_order += KPIxJO.new(
                {
                    "kpi_ids": [kpi.id],
                    "job_order_ids": self.job_order_ids.ids,
                }
            )

    def _context_filter_budget_info(self, item, date_to):
        ctx = super()._context_filter_budget_info(item, date_to)
        ctx["filter_job_order"] = item.job_order_id.id
        return ctx
