# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        compute="_compute_fund_id",
        readonly=False,
        store=True,
    )

    @api.depends("analytic_account_id")
    def _compute_fund_id(self):
        for rec in self:
            fund_ids = rec.analytic_account_id.budget_control_id.fund_ids
            rec.fund_id = len(fund_ids) == 1 and fund_ids.id or False

    @api.onchange("analytic_account_id")
    def _onchange_domain_analytic_account_id(self):
        # filter out, if not selected analytic account
        domain = [("id", "=", False)]
        analytic_id = self.analytic_account_id
        if analytic_id:
            domain = [("id", "in", analytic_id.budget_control_id.fund_ids.ids)]
        return {"domain": {"fund_id": domain}}

    def _check_fund_constraint(self):
        self.ensure_one()
        # FundConstraint = self.env["fund.constraint"]
        # FundConstraint.search([
        #     ("analytic_account_id", "=", self.analytic_account_id),
        #     ()
        # ])
        # x=1/0

    # def _prepare_budget_commitment(
    #     self,
    #     account,
    #     analytic_account,
    #     doc_date,
    #     amount_currency,
    #     currency,
    #     reverse=False,
    # ):
    #     res = super()._prepare_budget_commitment(
    #         account,
    #         analytic_account,
    #         doc_date,
    #         amount_currency,
    #         currency,
    #         reverse=reverse,
    #     )
    #     print(res)
    #     print("===========")
    #     return res

    def commit_budget(self, reverse=False):
        self.ensure_one()
        res = super().commit_budget()
        if self.move_id.state == "posted":
            self._check_fund_constraint()
        return res
