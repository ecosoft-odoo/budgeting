# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class GenerateBudgetControl(models.TransientModel):
    _inherit = "generate.budget.control"

    def _create_budget_controls(self, vals):
        budget_controls = super()._create_budget_controls(vals)
        # Recompute table kpi_x_job, as this will be used to reset plan.
        budget_controls._update_kpi_x_job_order()
        return budget_controls
