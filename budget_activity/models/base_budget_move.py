# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class BaseBudgetMove(models.AbstractModel):
    _inherit = "base.budget.move"

    activity_id = fields.Many2one(
        comodel_name="budget.activity",
        index=True,
        ondelete="restrict",
    )

    @api.constrains("activity_id", "account_id")
    def _check_activity_account(self):
        """Budget controlled by activity: the account of a budget move is the
        one of its activity, which the KPI relies on."""
        for rec in self:
            if (
                rec.company_id.budget_control_key == "activity_id"
                and rec.activity_id.account_id
                and rec.account_id
                and rec.account_id != rec.activity_id.account_id
            ):
                raise UserError(
                    self.env._(
                        "Account not equal to Activity's Account: %s",
                        rec.activity_id.account_id.display_name,
                    )
                )


class BudgetDoclineMixinBase(models.AbstractModel):
    _inherit = "budget.docline.mixin.base"

    activity_id = fields.Many2one(
        comodel_name="budget.activity",
        domain=lambda self: self._domain_activity(),
        index=True,
    )

    def _domain_activity(self):
        return []


class BudgetDoclineMixin(models.AbstractModel):
    _inherit = "budget.docline.mixin"

    required_activity = fields.Boolean(compute="_compute_required_activity", store=True)

    @api.depends("company_id.budget_control_key")
    def _compute_required_activity(self):
        for rec in self:
            rec.required_activity = rec.company_id.budget_control_key == "activity_id"

    def _update_budget_commitment(self, budget_vals, analytic, reverse=False):
        budget_vals = super()._update_budget_commitment(
            budget_vals, analytic, reverse=reverse
        )
        activity = self.activity_id
        budget_vals["activity_id"] = activity.id
        company = self.env["res.company"].browse(budget_vals["company_id"])
        if company.budget_control_key != "activity_id":
            return budget_vals
        # Returning an existing commitment is always possible
        if not reverse:
            self._check_budget_activity(company)
        # The budget move takes the account of the activity, even when the
        # document line books another account, e.g. the stock account of a
        # product valued in real time.
        if activity.account_id:
            budget_vals["account_id"] = activity.account_id.id
        return budget_vals

    def _check_budget_activity(self, company):
        """Budget controlled by activity: a line commits budget with an
        activity of its company (or a parent), mapped to an account. Without
        it, the line gets no KPI and escapes the budget check, unless its
        account bypasses the budget."""
        self.ensure_one()
        activity = self.activity_id.sudo()
        if not activity:
            if self.account_id.budget_bypass:
                return
            raise UserError(
                self.env._("Please select an activity on %s.", self.display_name)
            )
        if activity.company_id and activity.company_id not in company.parent_ids:
            raise UserError(
                self.env._(
                    "Company %(company)s is not allowed to use the activity "
                    "%(activity)s.",
                    company=company.name,
                    activity=activity.display_name,
                )
            )
        if not activity.account_id:
            raise UserError(
                self.env._(
                    "Please set the account of the activity %s.",
                    activity.display_name,
                )
            )
