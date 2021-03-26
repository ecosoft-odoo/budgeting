# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, models
from odoo.exceptions import UserError


class BudgetPeriod(models.Model):
    _inherit = "budget.period"

    def _prepare_controls_activity(self, budget_period, budget_moves):
        controls = set()
        control_analytics = budget_period.control_analytic_account_ids
        for i in budget_moves:
            if budget_period.control_all_analytic_accounts:
                if i.analytic_account_id and i.activity_id:
                    controls.add((i.analytic_account_id.id, i.activity_id.id))
            else:  # Only analtyic in control
                if (
                    i.analytic_account_id in control_analytics
                    and i.activity_id
                ):
                    controls.add((i.analytic_account_id.id, i.activity_id.id))
        # Convert to list of dict, for readibility
        return [{"analytic_id": x[0], "activity_id": x[1]} for x in controls]

    @api.model
    def _prepare_controls(self, budget_period, budget_moves):
        if budget_period.report_id.is_activity:
            return self._prepare_controls_activity(budget_period, budget_moves)
        return super()._prepare_controls(budget_period, budget_moves)

    @api.model
    def _get_kpi_by_control_key(self, instance, kpis, control):
        if instance.report_id.is_activity:
            activity_id = control["activity_id"]
            kpi = kpis.get(activity_id, False)
            if len(kpi) == 1:
                return kpi
            # Invalid KPI
            activity = self.env["budget.activity"].browse(activity_id)
            if not kpi:
                raise UserError(
                    _("Chosen activity %s is not valid for budgeting")
                    % activity.display_name
                )
            else:
                raise UserError(
                    _(
                        "KPI Template '%s' has more than one KPI being "
                        "refereced by same activity %s"
                    )
                    % (instance.report_id.name, activity.display_name)
                )
            return kpi
        return super()._get_kpi_by_control_key(instance, kpis, control)
