# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class BudgetDoclineMixin(models.AbstractModel):
    _inherit = "budget.docline.mixin"

    analytic_tag_all = fields.Many2many(
        comodel_name="account.analytic.tag",
        compute="_compute_fund_constraint",
        compute_sudo=True,
    )

    def _get_dimension_fields(self):
        if self.env.context.get("update_custom_fields"):
            return []  # Avoid to report these columns when not yet created
        return [x for x in self.fields_get().keys() if x.startswith("x_dimension_")]

    def _compute_analytic_tag_all(self):
        for doc in self:
            dimension_fields = doc._get_dimension_fields()
            analytic_tag_ids = doc[
                doc._budget_analytic_field
            ].fund_constraint_ids.mapped(doc._analytic_tag_field_name)
            doc.analytic_tag_all = analytic_tag_ids
            if (
                len(analytic_tag_ids) == len(dimension_fields)
                and doc.analytic_tag_ids
                and doc.analytic_tag_ids in analytic_tag_ids
            ):
                doc.analytic_tag_ids = analytic_tag_ids

    def _compute_fund_constraint(self):
        res = super()._compute_fund_constraint()
        self._compute_analytic_tag_all()
        return res

    def _check_fund_constraint_dimension(self):
        self.ensure_one()
        FundConstraint = self.env["fund.constraint"]
        analytic = self[self._budget_analytic_field]
        dimension_fields = self._get_dimension_fields()
        for dimension_field in dimension_fields:
            domain = [
                ("analytic_account_id", "=", analytic.id),
                (dimension_field, "=", self[dimension_field].id),
            ]
            fund_constraint_ids = FundConstraint.search(domain)
            fund_amount = fund_constraint_ids.mapped("fund_amount")
            balance_dimension = sum(fund_amount)
            balance = self._get_amount_balance()
            if balance > balance_dimension:
                raise UserError(
                    _(
                        "{} spent amount over limit {:,.2f} ({})".format(
                            self.name, (balance - balance_dimension), dimension_field
                        )
                    )
                )
        return True

    def check_fund_constraint(self):
        res = super().check_fund_constraint()
        self._check_fund_constraint_dimension()
        return res
