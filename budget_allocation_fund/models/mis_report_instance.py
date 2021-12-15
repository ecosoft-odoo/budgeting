# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class MisReportInstance(models.Model):
    _inherit = "mis.report.instance"

    def _get_context_filter_matrix(self):
        ctx = super()._get_context_filter_matrix()
        if ctx.get("mis_report_filters") and ctx.get("filter_fund_id"):
            ctx["mis_report_filters"]["fund_id"] = {
                "value": ctx["filter_fund_id"],
                "operator": "all",
            }
        return ctx
