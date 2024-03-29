# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class HRExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def action_submit_sheet(self):
        """As advance clearing, Employee Advance as activity not allowed"""
        if self.mapped("advance_sheet_id"):
            activity_advance = self.env.ref(
                "budget_activity_advance_clearing.activity_advance"
            )
            if activity_advance in self.mapped("expense_line_ids.activity_id"):
                raise UserError(
                    _(
                        "For clearing expenes, activity 'Employee Advance' "
                        "is not allowed.\nPlease change activity."
                    )
                )
        return super().action_submit_sheet()

    def get_domain_advance_sheet_expense_line(self):
        """Overwrite domain filter expense lines with clearing product or activity"""
        return self.advance_sheet_id.expense_line_ids.filtered(
            lambda x: x.clearing_product_id or x.clearing_activity_id
        )

    def _prepare_clear_advance(self, line):
        clearing_dict = super()._prepare_clear_advance(line)
        if line.clearing_activity_id:
            clearing_dict["activity_id"] = line.clearing_activity_id.id
            clearing_dict["name"] = line.name
        return clearing_dict

    def create_clearing_expense_line(self, line):
        clearing_line = super().create_clearing_expense_line(line)
        clearing_line._onchange_activity_id()
        return clearing_line


class HRExpense(models.Model):
    _inherit = "hr.expense"

    clearing_activity_id = fields.Many2one(
        comodel_name="budget.activity",
        string="Clearing Activity",
        domain=lambda self: [
            (
                "id",
                "!=",
                self.env.ref("budget_activity_advance_clearing.activity_advance", 0).id,
            )
        ],
        tracking=True,
        ondelete="restrict",
        index=True,
        help="Optional: On the clear advance, the clearing "
        "activity will create default activity line.",
    )

    @api.constrains("advance")
    def _check_advance(self):
        for expense in self.filtered("advance"):
            activity_advance = self.env.ref(
                "budget_activity_advance_clearing.activity_advance"
            )
            if not activity_advance.account_id:
                raise ValidationError(_("Employee advance activity has no account."))
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
