# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BudgetReportWizard(models.TransientModel):
    _name = "budget.report.wizard"
    _description = "Budget Report Wizard"

    budget_period_id = fields.Many2one(
        comodel_name="budget.period",
    )
    report_type = fields.Selection(
        selection=[
            ("budget", "Budget"),
            ("consumption", "Consumption"),
        ],
        default="budget",
    )
    date_from = fields.Date()
    date_to = fields.Date()
    analytic_account_ids = fields.Many2many(
        comodel_name="account.analytic.account",
    )

    @api.onchange("budget_period_id")
    def onchange_budget_period_id(self):
        self.date_from = self.budget_period_id.bm_date_from
        self.date_to = self.budget_period_id.bm_date_to

    def _get_report_base_filename(self):
        period = "{} - ".format(self.budget_period_id.name)
        return "{}BudgetReport".format(self.budget_period_id and period or "")

    def _get_view_report(self):
        """Hooks this function to add action report"""
        return "budget_control_report.action_export_budget_xlsx"

    def run_report_excel(self):
        view_report = self._get_view_report()
        return self.env.ref(view_report).sudo().report_action(self, config=False)
