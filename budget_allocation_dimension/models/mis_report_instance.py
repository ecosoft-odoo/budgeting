# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class MisReportInstance(models.Model):
    _inherit = "mis.report.instance"

    def _get_context_filter_matrix(self):
        ctx = super()._get_context_filter_matrix()
        if ctx.get("mis_report_filters") and ctx.get("filter_analytic_tag_ids"):
            ctx["mis_report_filters"]["analytic_tag_ids"] = {
                "value": ctx["filter_analytic_tag_ids"],
                "operator": "all",
            }
        return ctx
