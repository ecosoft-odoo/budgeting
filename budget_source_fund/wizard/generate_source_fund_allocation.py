# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class GenerateSourceFundAllocation(models.TransientModel):
    _name = "generate.source.fund.allocation"
    _description = "Generate Source of Fund Allocation"

    budget_period_id = fields.Many2one(
        comodel_name="budget.period",
        required=True,
        default=lambda self: self._get_budget_period_id(),
        ondelete="cascade",
    )
    budget_id = fields.Many2one(
        comodel_name="mis.budget",
        related="budget_period_id.mis_budget_id",
    )
    analytic_group_ids = fields.Many2many(
        comodel_name="account.analytic.group",
        relation="analytic_group_generate_source_fund_allocation_rel",
        column1="wizard_id",
        column2="group_id",
    )
    all_analytic_accounts = fields.Boolean(
        help="Generate all analytic account from analytic group",
    )
    analytic_account_ids = fields.Many2many(
        comodel_name="account.analytic.account",
        relation="analytic_generate_source_fund_allocation_rel",
        column1="wizard_id",
        column2="anlaytic_id",
        domain="[('group_id', 'in', analytic_group_ids)]",
    )

    @api.model
    def view_init(self, fields):
        budget_source_fund_allocation = self._get_source_fund_allocation()
        for rec in budget_source_fund_allocation:
            if rec.state != "draft":
                raise UserError(
                    _("Budget Allocation have to state 'draft' only.")
                )
        return False

    @api.model
    def _get_source_fund_allocation(self):
        active_id = self._context.get("active_id")
        return self.env["budget.source.fund.plan"].browse(active_id)

    @api.model
    def _get_budget_period_id(self):
        allocation_id = self._get_source_fund_allocation()
        return allocation_id.budget_period_id

    @api.onchange("all_analytic_accounts", "analytic_group_ids")
    def _onchange_analytic_accounts(self):
        """Auto fill analytic_account_ids."""
        AnalyticAccount = self.env["account.analytic.account"]
        self.analytic_account_ids = False
        if self.all_analytic_accounts:
            self.analytic_account_ids = AnalyticAccount.search(
                [("group_id", "in", self.analytic_group_ids.ids)]
            )

    def action_generate_line(self):
        self.ensure_one()
        AllocationLine = self.env["budget.source.fund.allocation"]
        budget_source_fund_allocation = self._get_source_fund_allocation()
        # Find existing allocation, so we can skip.
        existing_analytics = (
            budget_source_fund_allocation.allocation_line.mapped(
                "analytic_account_id"
            )
        )
        # Create budget controls that are not already exists
        new_analytic = self.analytic_account_ids - existing_analytics
        vals = [{"analytic_account_id": x.id} for x in new_analytic]
        vals = map(
            lambda l: {
                "allocation_id": budget_source_fund_allocation.id,
                "budget_period_id": self.budget_period_id.id,
                "date_from": self.budget_period_id.bm_date_from,
                "date_to": self.budget_period_id.bm_date_to,
                "analytic_account_id": l["analytic_account_id"],
            },
            vals,
        )
        allocation_line_id = AllocationLine.create(list(vals))
        return allocation_line_id
