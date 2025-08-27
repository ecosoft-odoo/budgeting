# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetConsumptionReportWizard(models.TransientModel):
    _name = "budget.consumption.report.wizard"
    _inherit = "budget.report.wizard"
    _description = "Budget Consumption Report Wizard"

    amount_type = fields.Selection(
        selection=lambda self: self.env[
            "budget.monitor.report"
        ]._get_budget_amount_type(),
        string="Type",
    )

    def _get_report_base_filename(self):
        if self.report_type == "consumption":
            period = "{} - ".format(self.budget_period_id.name)
            return "{}BudgetConsumptionReport".format(
                self.budget_period_id and period or ""
            )
        return super()._get_report_base_filename()

    def _get_view_report(self):
        if self.report_type == "consumption":
            return "budget_control_report.action_export_budget_consumption_xlsx"
        return super()._get_view_report()
