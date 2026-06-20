# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountAnalyticPlan(models.Model):
    _inherit = "account.analytic.plan"

    budget_actual_source_default = fields.Selection(
        selection=lambda self: self._selection_budget_actual_source(),
        string="Default Budget Actual Source",
        default="bill",
        help="Default actual source for analytics in this plan. "
        "Empty = use default (bill).",
    )

    @api.model
    def _selection_budget_actual_source(self):
        return [("bill", "Bill / Invoice")]
