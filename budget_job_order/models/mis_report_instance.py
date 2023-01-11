# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class MisReportInstance(models.Model):
    _inherit = "mis.report.instance"

    def _get_context_filter_matrix(self):
        ctx = super()._get_context_filter_matrix()
        job_order = self._context.get("filter_job_order", False)
        if ctx.get("mis_report_filters") and job_order:
            if job_order == [False]:
                job_order = False
            ctx["mis_report_filters"]["job_order_id"] = {
                "value": job_order,
                "operator": "all",
            }
        return ctx
