# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class BaseBudgetMove(models.AbstractModel):
    _name = "base.budget.move"
    _description = "Abstract class to be extended by budgt commit documents"

    date = fields.Date(
        required=True,
        index=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
    )
    account_id = fields.Many2one(
        comodel_name="account.account",
        string="Account",
        auto_join=True,
        index=True,
        readonly=True,
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Analytic Account",
        auto_join=True,
        index=True,
        readonly=True,
    )
    analytic_group = fields.Many2one(
        comodel_name="account.analytic.group",
        string="Analytic Group",
        auto_join=True,
        index=True,
        readonly=True,
    )
    analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        string="Analytic Tags",
    )
    amount_currency = fields.Float(
        required=True,
        help="Amount in multi currency",
    )
    credit = fields.Float(
        readonly=True,
    )
    debit = fields.Float(
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.user.company_id.id,
        index=True,
    )


class BudgetDoclineMixin(models.AbstractModel):
    _name = "budget.docline.mixin"
    _description = "Mixin used in each document line model that commit budget"
    _analytic_field = "analytic_account_id"
    _doc_date_fields = []  # Date used for budget commitment

    amount_commit = fields.Float(
        compute="_compute_commit",
        copy=False,
        store=True,
    )
    date_commit = fields.Date(
        compute="_compute_commit",
        store=True,
        copy=False,
        readonly=False,  # Allow manual entry of this field
    )

    def _filter_current_move(self, analytic):
        self.ensure_one()
        return self.budget_move_ids.filtered(
            lambda l: l.analytic_account_id == analytic
        )

    @api.depends("budget_move_ids", "budget_move_ids.date")
    def _compute_commit(self):
        """
        - Calc amount_commit from all budget_move_ids
        - Calc date_commit if not exists and on 1st budget_move_ids only or False
        """
        for rec in self:
            debit = sum(rec.budget_move_ids.mapped("debit"))
            credit = sum(rec.budget_move_ids.mapped("credit"))
            rec.amount_commit = debit - credit
            if rec.budget_move_ids:
                rec.date_commit = min(rec.budget_move_ids.mapped("date"))
            else:
                rec.date_commit = False

    def _set_date_commit(self):
        """Default implementation, use date from _doc_date_field
        which is mostly write_date during budget commitment"""
        self.ensure_one()
        docline = self
        if docline.date_commit:
            return
        if not self._doc_date_fields:
            raise ValidationError(_("'_doc_date_fields' is not set!"))
        analytic = docline[self._analytic_field]
        if not analytic:
            docline.date_commit = False
            return
        # Get dates following _doc_date_fields
        dates = [
            docline.mapped(f)[0]
            for f in self._doc_date_fields
            if docline.mapped(f)[0]
        ]
        if dates:
            if isinstance(dates[0], datetime):
                docline.date_commit = fields.Datetime.context_timestamp(
                    self, dates[0]
                )
            else:
                docline.date_commit = dates[0]
        else:
            docline.date_commit = False
        # If the date_commit is not in analytic date range, use possible date.
        analytic._auto_adjust_date_commit(docline)

    def _prepare_budget_commitment(
        self,
        account,
        analytic_account,
        doc_date,
        amount_currency,
        currency,
        reverse=False,
    ):
        self.ensure_one()
        company = self.env.user.company_id
        amount = (
            currency
            and currency._convert(
                amount_currency, company.currency_id, company, doc_date
            )
            or amount_currency
        )
        # By default, commit date is equal to document date
        # this is correct for normal case, but may require different date
        # in case of budget that carried to new period/year
        commit_date = (
            self._context.get("force_commit_date")
            or doc_date
            or fields.Date.context_today(self)
        )
        res = {
            "product_id": self.product_id.id,
            "account_id": account.id,
            "analytic_account_id": analytic_account.id,
            "analytic_group": analytic_account.group_id.id,
            "date": commit_date,
            "amount_currency": amount_currency,
            "debit": not reverse and amount or 0,
            "credit": reverse and amount or 0,
            "company_id": company.id,
        }
        if sum([res["debit"], res["credit"]]) < 0:
            res["debit"], res["credit"] = abs(res["credit"]), abs(res["debit"])
        return res

    def commit_budget(self):
        pass

    def _required_fields_to_commit(self):
        return [self._analytic_field]

    def can_commit(self):
        self.ensure_one()
        dom = [(f, "!=", False) for f in self._required_fields_to_commit()]
        docline = self.filtered_domain(dom)
        if not docline:
            return False
        docline._set_date_commit()
        docline._check_date_commit()  # Testing only, can be removed when stable.
        return True

    def _check_date_commit(self):
        """ Commit date must inline with analytic account """
        self.ensure_one()
        docline = self
        analytic = docline[self._analytic_field]
        if analytic:
            if not docline.date_commit:
                raise UserError(_("No budget commitment date"))
            date_from = analytic.bm_date_from
            date_to = analytic.bm_date_to
            if (date_from and date_from > docline.date_commit) or (
                date_to and date_to < docline.date_commit
            ):
                raise UserError(
                    _("Budget date commit is not within date range of - %s")
                    % analytic.display_name
                )
        else:
            if docline.date_commit:
                raise UserError(_("Budget commitment date not required"))
