# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BudgetControl(models.Model):
    _inherit = "budget.control"

    def create_revision(self):
        """Allow revision with edit amount"""
        return super(BudgetControl, self.with_context(edit_amount=1)).create_revision()


class BudgetControlLine(models.Model):
    _inherit = "budget.control.line"

    is_readonly = fields.Boolean(compute="_compute_amount_readonly")

    @api.depends("budget_control_id")
    def _compute_amount_readonly(self):
        lock_amount = self.env.company.budget_control_revision_lock_amount
        date = fields.Date.context_today(self)
        # Change current month to previous month
        if lock_amount == "last":
            date = date.replace(day=1) - relativedelta(days=1)
        for rec in self:
            rec.is_readonly = False
            if (
                rec.budget_control_id.init_revision
                or lock_amount == "none"
                or rec.date_from > date
            ):
                continue
            rec.is_readonly = True

    @api.constrains("amount")
    def _check_amount_readonly(self):
        """Skip check amount with context edit_amount (if any)"""
        edit_amount = self._context.get("edit_amount", False)
        if edit_amount:
            return
        readonly_lines = self.filtered(lambda l: l.is_readonly)
        if readonly_lines:
            raise UserError(_("You can not edit past amount."))
