# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class MisReportInstance(models.Model):
    _inherit = "mis.report.instance"

    def _compute_matrix(self):
        """ Add possible filter_analytic_ids to compute """
        ctx = self.env.context.copy()
        if ctx.get("filter_analytic_ids"):
            ctx["mis_report_filters"] = ctx.get("mis_report_filters", {})
            ctx["mis_report_filters"]["analytic_account_id"] = {
                "value": ctx["filter_analytic_ids"],
                "operator": "all",
            }
        if ctx.get("filter_activity_group"):
            ctx["mis_report_filters"]["activity_group_id"] = {
                "value": ctx["filter_activity_group"],
                "operator": "all",
            }
        if ctx.get("filter_period_date_from"):
            ctx["mis_report_filters"]["date"] = {
                "value": ctx["filter_period_date_from"],
                "operator": ">=",
            }
        if ctx.get("filter_period_date_to"):
            ctx["mis_report_filters"]["date"] = {
                "value": ctx["filter_period_date_to"],
                "operator": "<=",
            }
        return super(
            MisReportInstance, self.with_context(ctx)
        )._compute_matrix()
