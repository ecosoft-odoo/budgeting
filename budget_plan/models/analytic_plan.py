# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountAnalyticPlan(models.Model):
    _inherit = "account.analytic.plan"

    @api.model
    def _get_budget_column_models(self):
        """Plan line details hold the accounts of their dimensions."""
        return super()._get_budget_column_models() + ["budget.plan.line.detail"]

    @api.model
    def _check_budget_moves_unused(self, analytics, message):
        res = super()._check_budget_moves_unused(analytics, message)
        # Plan lines hold their budget analytic
        if (
            self.env["budget.plan.line"]
            .sudo()
            .search_count([("analytic_account_id", "in", analytics.ids)], limit=1)
        ):
            raise UserError(message)
        return res


class AccountAnalyticApplicability(models.Model):
    _inherit = "account.analytic.applicability"

    business_domain = fields.Selection(
        selection_add=[("budget", "Budget Plan")],
        ondelete={"budget": "cascade"},
    )
