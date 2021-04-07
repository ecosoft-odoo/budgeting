# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, fields, models
from odoo.exceptions import UserError


class BaseFundConstraint(models.AbstractModel):
    _name = "base.fund.constraint.commit"
    _description = "Base fund constraint for commitment"
    _doc_line_field = False

    def check_fund_constraint(self):
        """ Check Fund Constraint per docline line """
        FundConstraint = self.env["fund.constraint"]
        for doc in self:
            if not doc._doc_line_field:
                continue
            for line in doc[doc._doc_line_field].filtered("fund_id"):
                analytic = line[line._fund_analytic_field]
                domain = [
                    ("analytic_account_id", "=", analytic.id),
                    ("fund_id", "=", line.fund_id.id),
                ]
                fund_constraint_ids = FundConstraint.search(domain)
                balance = line._get_amount_balance()
                fund_over_limit = fund_constraint_ids.filtered(
                    lambda l: l.fund_amount < balance
                )
                for fc in fund_over_limit:
                    over_limit = balance - fc.fund_amount
                    raise UserError(
                        _(
                            "{} spent fund amount over limit {:,.2f} {}".format(
                                line.name, over_limit, fc.currency_id.symbol
                            )
                        )
                    )
        return True


class FundDoclineMixin(models.AbstractModel):
    _name = "fund.docline.mixin"
    _description = (
        "Mixin used in each document line model that fund constraint"
    )
    _fund_analytic_field = "analytic_account_id"
    _amount_balance_field = False

    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        compute="_compute_fund_constraint",
        compute_sudo=True,
        readonly=False,
        store=True,
    )
    fund_all = fields.Many2many(
        comodel_name="budget.source.fund",
        compute="_compute_fund_constraint",
        compute_sudo=True,
    )

    def _compute_fund_constraint(self):
        for doc in self:
            fund_ids = doc[
                doc._fund_analytic_field
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
