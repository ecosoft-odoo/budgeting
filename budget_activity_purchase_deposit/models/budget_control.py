# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    def _get_lines_init_date(self):
        self.ensure_one()
        lines = super()._get_lines_init_date()
        kpi_deposit = self.env.ref(
            "budget_activity_purchase_deposit.budget_kpi_purchase_deposit"
        )
        return lines.filtered(lambda l: l.kpi_id != kpi_deposit)
