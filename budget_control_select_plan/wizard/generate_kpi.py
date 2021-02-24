# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class GenerateKPI(models.TransientModel):
    _name = "generate.kpi"
    _description = "Generate KPI"

    budget_control_id = fields.Many2one(
        comodel_name="budget.control",
        default=lambda self: self._get_budget_control_id(),
        readonly=True,
    )
    mis_report_id = fields.Many2one(
        comodel_name="mis.report",
        related="budget_control_id.budget_id.report_id",
    )
    kpi_ids = fields.Many2many(
        comodel_name="mis.report.kpi",
        relation="report_mis_report_rel",
        column1="mis_report_id",
        column2="report_id",
        domain="[('report_id', '=', mis_report_id)]",
    )

    @api.model
    def _get_budget_control_id(self):
        active_id = self._context.get("active_id", False)
        return self.env["budget.control"].browse(active_id)

    def action_generate_plan(self):
        self.budget_control_id.with_context(
            {"kpi_ids": self.kpi_ids.ids}
        ).prepare_budget_control_matrix()
        return True
