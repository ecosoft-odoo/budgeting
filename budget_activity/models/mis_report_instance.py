# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class MisReportInstance(models.Model):
    _inherit = "mis.report.instance"

    def _get_context_filter_matrix(self):
        ctx = super()._get_context_filter_matrix()
        if ctx.get("filter_analytic_ids") and ctx.get("filter_activity_group"):
            ctx["mis_report_filters"]["activity_group_id"] = {
                "value": ctx["filter_activity_group"],
                "operator": "all",
            }
        return ctx
