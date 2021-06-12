# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError


class HRExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def action_submit_sheet(self):
        """ As advance clearing, Employee Advance as activity not allowed """
        activity_advance = self.env.ref(
            "budget_activity_advance_clearing.activity_advance"
        )
        if activity_advance in self.mapped("expense_line_ids.activity_id"):
            raise UserError(
                _(
                    "For clearing expenes, activity 'Employee Advance' not allowed.\n"
                    "Please change activity."
                )
            )
        return super().action_submit_sheet()


class HRExpense(models.Model):
    _inherit = "hr.expense"

    @api.constrains("advance")
    def _check_advance(self):
        for expense in self.filtered("advance"):
            activity_advance = self.env.ref(
                "budget_activity_advance_clearing.activity_advance"
            )
            if not activity_advance.account_id:
                raise ValidationError(
                    _("Employee advance activity has no account.")
                )
            if expense.activity_id != activity_advance:
                raise ValidationError(
                    _("Employee advance, selected activity is not valid.")
                )
        return super()._check_advance()

    @api.onchange("advance")
    def onchange_advance(self):
        res = super().onchange_advance()
        if self.advance:
            self.activity_id = self.env.ref(
                "budget_activity_advance_clearing.activity_advance"
            )
        else:
            self.activity_id = False
        return res
