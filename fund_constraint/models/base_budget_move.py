# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, fields, models
from odoo.exceptions import UserError


class BaseBudgetMove(models.AbstractModel):
    _inherit = "base.budget.move"

    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        string="Fund",
        index=True,
    )


class BudgetDoclineMixin(models.AbstractModel):
    _inherit = "budget.docline.mixin"
    _amount_balance_field = False

    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        index=True,
        ondelete="restrict",
    )
    fund_all = fields.Many2many(
        comodel_name="budget.source.fund",
        compute="_compute_fund_constraint",
        compute_sudo=True,
    )

    def _compute_fund_constraint(self):
        for doc in self:
            fund_ids = doc[
                doc._budget_analytic_field
            ].fund_constraint_ids.mapped("fund_id")
            doc.fund_all = fund_ids
            if len(fund_ids) > 1 and doc.fund_id and doc.fund_id in fund_ids:
                continue
            doc.fund_id = len(fund_ids) == 1 and fund_ids.id or False

    def _get_amount_balance(self):
        self.ensure_one()
        if not self._amount_balance_field:
            return 0.0
        return self[self._amount_balance_field]

    def _update_budget_commitment(self, budget_vals, reverse=False):
        budget_vals = super()._update_budget_commitment(
            budget_vals, reverse=reverse
        )
        budget_vals["fund_id"] = self.fund_id.id
        return budget_vals

    def check_fund_constraint(self):
        """ Check Fund Constraint per docline line """
        FundConstraint = self.env["fund.constraint"]
        self.ensure_one()
        analytic = self[self._budget_analytic_field]
        domain = [
            ("analytic_account_id", "=", analytic.id),
            ("fund_id", "=", self.fund_id.id),
        ]
        fund_constraint_ids = FundConstraint.search(domain)
        balance = self._get_amount_balance()
        fund_over_limit = fund_constraint_ids.filtered(
            lambda l: l.fund_amount < balance
        )
        for fc in fund_over_limit:
            over_limit = balance - fc.fund_amount
            raise UserError(
                _(
                    "{} spent fund amount over limit {:,.2f} {}".format(
                        self.name, over_limit, fc.currency_id.symbol
                    )
                )
            )
        return True
