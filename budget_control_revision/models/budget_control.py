# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class BudgetControl(models.Model):
    _name = "budget.control"
    _inherit = ["budget.control", "base.revision"]
    _order = "revision_number desc, analytic_account_id"

    current_revision_id = fields.Many2one(
        comodel_name="budget.control",
    )
    old_revision_ids = fields.One2many(
        comodel_name="budget.control",
    )
    init_revision = fields.Boolean(
        compute="_compute_init_revision",
        store=True,
    )
    date_range_readonly = fields.Many2one(
        comodel_name="date.range",
        compute="_compute_date_range_readonly",
    )

    # Add budget_period_id and analytic account for check constrains
    _sql_constraints = [
        (
            "revision_unique",
            "unique(\
                unrevisioned_name, \
                revision_number, \
                budget_period_id, \
                analytic_account_id\
            )",
            "Reference and revision must be unique.",
        )
    ]

    @api.depends("revision_number")
    def _compute_init_revision(self):
        for rec in self:
            rec.init_revision = not rec.revision_number

    def _compute_date_range_readonly(self):
        for rec in self:
            line_readonly = rec.line_ids.filtered(lambda line: line.is_readonly)
            rec.date_range_readonly = (
                max(
                    line_readonly.mapped("date_range_id"),
                    key=lambda line: line.date_end,
                )
                if line_readonly
                else False
            )

    def _filter_by_budget_control(self, val):
        res = super()._filter_by_budget_control(val)
        if val["amount_type"] != "10_budget":
            return res
        revision_number = (
            0 if not val["revision_number"] else int(val["revision_number"])
        )
        return res and revision_number == self.revision_number

    def action_create_revision(self):
        if any(rec.state != "cancel" for rec in self):
            raise UserError(
                self.env._(
                    "Budget control can only be revision "
                    "when it is in the 'cancel' state."
                )
            )
        return self.create_revision()

    def create_revision(self):
        """Not checked amount when revision"""
        return super(BudgetControl, self.with_context(edit_amount=1)).create_revision()


class BudgetControlLine(models.Model):
    _inherit = "budget.control.line"

    is_readonly = fields.Boolean(
        compute="_compute_amount_readonly",
    )

    @api.depends("budget_control_id")
    def _compute_amount_readonly(self):
        lock_amount = self.env.company.budget_control_revision_lock_amount
        date = fields.Date.context_today(self)
        # Change current month to previous month
        if lock_amount == "last":
            date = date.replace(day=1) - relativedelta(days=1)

        for rec in self:
            rec.is_readonly = not (
                rec.budget_control_id.init_revision
                or lock_amount == "none"
                or rec.date_from > date
            )

    @api.constrains("amount")
    def _check_amount_readonly(self):
        """Skip check amount with context edit_amount (if any)"""
        edit_amount = self.env.context.get("edit_amount", False)
        if edit_amount:
            return

        if any(rec.is_readonly for rec in self):
            raise UserError(self.env._("You can not edit past amount."))
