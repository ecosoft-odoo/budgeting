# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class BaseBudgetMove(models.AbstractModel):
    _inherit = "base.budget.move"

    activity_id = fields.Many2one(
        comodel_name="budget.activity",
        index=True,
    )
    account_id = fields.Many2one(
        compute="_compute_activity_account",
        store=True,
        help="When activity is selected, always use activity's account to "
        "enusre that the KPI budgeting which rely on account is valid. "
        "Because in some case, i.e., perpetual inventory, "
        "account in account.move.line can be different with "
        "account in account.budget.move.",
    )

    @api.depends("activity_id")
    def _compute_activity_account(self):
        if self.env.company.budget_control_key == "activity_id":
            for rec in self:
                rec.account_id = (
                    rec.activity_id.account_id if rec.activity_id else rec.account_id
                )

    @api.constrains("activity_id", "account_id")
    def _check_activity_account(self):
        if self.env.company.budget_control_key != "activity_id":
            return

        records = self.filtered(lambda r: r.activity_id and r.account_id)
        for rec in records:
            if rec.account_id.id != rec.activity_id.account_id.id:
                raise UserError(
                    self.env._("Account not equal to Activity's Account: %s")
                    % rec.activity_id.account_id.display_name
                )


class BudgetDoclineMixinBase(models.AbstractModel):
    _inherit = "budget.docline.mixin.base"

    activity_id = fields.Many2one(
        comodel_name="budget.activity",
        string="Activity",
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
        budget_vals["activity_id"] = self.activity_id.id
        # For case object without account_id (PR/PO), normally account is from
        # product, it should now changed to follow activity.
        # But if account_id is part of object (INV), use whatever is passed-in.
        if "account_id" not in self:
            budget_vals["account_id"] = self["activity_id"].account_id.id
        return budget_vals
