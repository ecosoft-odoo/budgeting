# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import ast

from odoo import api, fields, models


class MisReportKpi(models.Model):
    _inherit = "mis.report.kpi"

    description = fields.Char(
        compute="_compute_name_activity", store=True, readonly=False
    )
    activity_expression = fields.Boolean(
        compute="_compute_is_activity",
        readonly=False,
        store=True,
    )
    budget_activity_group = fields.Many2one(
        comodel_name="budget.activity.group",
        string="Activity Group",
    )
    respectively_variation = fields.Char(
        help="respectively variation over the "
        "period (p), initial balance (i), ending balance (e)"
    )

    @api.depends("budget_activity_group")
    def _compute_name_activity(self):
        for rec in self:
            rec.description = False
            if rec.activity_expression and rec.budget_activity_group:
                rec.description = rec.budget_activity_group.name

    @api.depends("report_id.is_activity")
    def _compute_is_activity(self):
        for rec in self:
            rec.activity_expression = rec.report_id.is_activity

    def _filter_balance_mis(self, activity_ids):
        self.ensure_one()
        dom = "('activity_id', 'in', {})".format(tuple(activity_ids.ids))
        return dom

    @api.depends(
        "expression_ids.subkpi_id.name",
        "expression_ids.name",
        "budget_activity_group.activity_ids",
        "respectively_variation",
    )
    def _compute_expression(self):
        super()._compute_expression()
        for kpi in self:
            if kpi.activity_expression and kpi.budget_activity_group:
                activity_ids = kpi.budget_activity_group.activity_ids
                account_ids = activity_ids.mapped("account_id")
                account_str = [
                    ast.literal_eval(acc.code) for acc in account_ids
                ]
                kpi.expression = "bal{}{}[{}]".format(
                    kpi.respectively_variation or "",
                    account_str,
                    kpi._filter_balance_mis(activity_ids),
                )
                # Update expression_ids for display realtime
                kpi._inverse_expression()
