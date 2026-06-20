# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountAnalyticPlan(models.Model):
    _inherit = "account.analytic.plan"

    @api.model
    def _selection_budget_actual_source(self):
        return super()._selection_budget_actual_source() + [
            ("stock_done", "Stock Done (Outgoing Picking)"),
        ]
