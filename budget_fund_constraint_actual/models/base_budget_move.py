# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BaseBudgetMove(models.AbstractModel):
    _inherit = "base.budget.move"

    fund_id = fields.Many2one(comodel_name="budget.source.fund", index=True)


class BudgetDoclineMixin(models.AbstractModel):
    _inherit = "budget.docline.mixin"

    fund_id = fields.Many2one(comodel_name="budget.source.fund", index=True)

    def _prepare_budget_commitment(
        self,
        account,
        analytic_account,
        doc_date,
        amount_currency,
        currency,
        reverse=False,
    ):
        res = super()._prepare_budget_commitment(
            account,
            analytic_account,
            doc_date,
            amount_currency,
            currency,
            reverse=reverse,
        )
        res["fund_id"] = self.fund_id.id
        return res
