# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class GenerateBudgetControl(models.TransientModel):
    _inherit = "generate.budget.control"

    def _create_budget_controls(self, vals):
        """Add kpi_ids into tabel kpi_x_job"""
        for val in vals:
            kpi_ids = val.get("kpi_ids", False)
            if kpi_ids:
                val["kpi_x_job_order"] = [
                    (
                        0,
                        0,
                        {
                            "job_order_ids": False,
                            "kpi_ids": kpi_ids,
                        },
                    )
                ]
        return super()._create_budget_controls(vals)
