# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.exceptions import UserError


class BudgetActivity(models.Model):
    _inherit = "budget.activity"
    _rec_names_search = ["name", "keyword_ids", "account_id"]

    kpi_id = fields.Many2one(
        comodel_name="budget.kpi",
        index=True,
    )
    account_id = fields.Many2one(
        comodel_name="account.account",
        check_company=True,
        index=True,
    )

    def write(self, vals):
        if "account_id" in vals:
            self._check_account_used(vals["account_id"])
        return super().write(vals)

    def _check_account_used(self, account_id):
        """Budget moves of an activity take its account: it cannot change once
        they exist."""
        activities = self.filtered(
            lambda activity: activity.account_id.id != (account_id or False)
        )
        if not activities:
            return
        for model in self.env["account.analytic.plan"]._get_budget_move_models():
            if (
                self.env[model]
                .sudo()
                .with_context(active_test=False)
                .search_count([("activity_id", "in", activities.ids)], limit=1)
            ):
                raise UserError(
                    self.env._(
                        "You cannot change the account because "
                        "it is already used in a commit."
                    )
                )
