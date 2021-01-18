# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import ast

from odoo import api, fields, models


class MisReportKpi(models.Model):
    _inherit = "mis.report.kpi"

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
    not_affect_budget = fields.Boolean(
        default=True, help="If check, Does not affect the budget."
    )

    @api.depends("report_id.is_activity")
    def _compute_is_activity(self):
        for rec in self:
            rec.activity_expression = rec.report_id.is_activity

    def _filter_balance_mis(self, activity_ids):
        self.ensure_one()
        dom = "('activity_id', 'in', {})".format(tuple(activity_ids.ids))
        if self.not_affect_budget:
            not_affect_budget = (
                "'|', ('move_id', '=', False), "
                "('move_id.not_affect_budget', '=', False)"
            )
            dom = ", ".join([dom, not_affect_budget])
        return dom

    @api.depends(
        "expression_ids.subkpi_id.name",
        "expression_ids.name",
        "budget_activity_group.activity_ids",
        "respectively_variation",
        "not_affect_budget",
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
