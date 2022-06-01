# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


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
    activity_group_id = fields.Many2one(
        comodel_name="budget.activity.group",
        index=True,
        string="Activity Group",
    )
    respectively_variation = fields.Char(
        help="respectively variation over the "
        "period (p), initial balance (i), ending balance (e)"
    )

    @api.depends("activity_group_id")
    def _compute_name_activity(self):
        for rec in self:
            rec.description = False
            if rec.activity_expression and rec.activity_group_id:
                rec.description = rec.activity_group_id.name

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
        "activity_group_id.activity_ids",
        "respectively_variation",
    )
    def _compute_expression(self):
        super()._compute_expression()
        for kpi in self:
            if kpi.activity_expression and kpi.activity_group_id:
                activity_ids = kpi.activity_group_id.activity_ids
                if not activity_ids:
                    raise UserError(
                        _(
                            "Activity Group {} is not activity.".format(
                                kpi.activity_group_id.name
                            )
                        )
                    )
                accounts = activity_ids.mapped("account_id")
                account_str = "[%s]" % ",".join([acc.code for acc in accounts])
                kpi.expression = "bal{}{}[{}]".format(
                    kpi.respectively_variation or "",
                    account_str,
                    kpi._filter_balance_mis(activity_ids),
                )
                # Update expression_ids for display realtime
                # TODO: please check follwoing logic again.
                kpi._inverse_expression()
