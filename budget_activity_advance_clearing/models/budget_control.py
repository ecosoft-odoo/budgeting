# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    def _get_lines_init_date(self):
        self.ensure_one()
        lines = super()._get_lines_init_date()
        kpi_advance = self.env.ref(
            "budget_activity_advance_clearing.budget_kpi_advance"
        )
        return lines.filtered(lambda l: l.kpi_id != kpi_advance)
