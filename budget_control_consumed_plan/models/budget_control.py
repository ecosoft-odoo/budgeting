# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    def _context_filter_budget_info(self, item, date_to):
        ctx = self._context.copy()
        ctx.update(
            {
                "filter_activity_group": item.activity_group_id.id,
                "filter_period_date_from": item.date_from,
                "filter_period_date_to": date_to,
            }
        )
        return ctx

    def _update_consumed_value(self, item_ids, date):
        analytic_id = [self.analytic_account_id.id]
        budget_period = self.budget_period_id
        for item in item_ids:
            date_to = item.date_to
            if item.date_from <= date <= item.date_to:
                date_to = date
            ctx = self._context_filter_budget_info(item, date_to)
            info = budget_period.with_context(ctx).get_budget_info(analytic_id)
            item.write({"amount": info["amount_consumed"]})

    def _update_kpi_reset_plan(self, kpis):
        self.ensure_one()
        if kpis:
            self.kpi_ids = [(4, x.id) for x in list(set(kpis))]

    def _get_new_kpis(self):
        kpis = self.env["mis.report.kpi"]
        # Prepare result matrix for all analytic_id
        analytic_ids = self.analytic_account_id.ids
        instance = self.budget_period_id.report_instance_id
        kpi_matrix = self.budget_period_id._prepare_matrix_all_analytics(
            instance, analytic_ids
        )
        kpi_ids = self.item_ids.mapped("kpi_expression_id.kpi_id").ids
        # Check kpi is not plan, it will update new activity group.
        for row in kpi_matrix.iter_rows():
            if row.kpi.id in kpi_ids:
                continue
            budgetable = row.kpi.budgetable
            for cell in row.iter_cells():
                if cell.val > 0.0 and budgetable:
                    kpis += cell.row.kpi
        return kpis

    def _get_consumed_plan(self, date):
        """
        Update consumed amount (actual + commit)
        since first date to current day.
        """
        self.ensure_one()
        kpis = self._get_new_kpis()
        self._update_kpi_reset_plan(kpis)
        self.sudo().with_context(
            keep_item_amount=True
        ).prepare_budget_control_matrix()
        # Filter date range to current month
        item_ids = self.item_ids.filtered(lambda l: l.date_from <= date)
        self._update_consumed_value(item_ids, date)

    def update_consumed_plan(self, date=False):
        if not date:
            date = fields.Date.context_today(self)
        for rec in self:
            rec._get_consumed_plan(date)
        return True

    def action_update_consumed_plan(self):
        group_manual_date_consumed_plan = self.env.user.has_group(
            "budget_control_consumed_plan.group_manual_date_consumed_plan"
        )
        if group_manual_date_consumed_plan:
            return {
                "name": _("Updating Consumed Plan"),
                "res_model": "update.consumed.plan",
                "view_mode": "form",
                "context": self._context,
                "target": "new",
                "type": "ir.actions.act_window",
            }
        return self.update_consumed_plan()
