# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HRExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def get_domain_advance_sheet_expense_line(self):
        """Overwrite domain filter expense lines with clearing product or activity"""
        return self.advance_sheet_id.expense_line_ids.filtered(
            lambda exp: exp.clearing_product_id or exp.clearing_activity_id
        )

    def _prepare_clear_advance(self, line):
        clearing_dict = super()._prepare_clear_advance(line)
        if line.clearing_activity_id:
            clearing_dict["activity_id"] = line.clearing_activity_id.id
            clearing_dict["account_id"] = line.clearing_activity_id.account_id.id
            clearing_dict["name"] = line.name
        return clearing_dict


class HRExpense(models.Model):
    _inherit = "hr.expense"

    clearing_activity_id = fields.Many2one(
        comodel_name="budget.activity",
        tracking=True,
        ondelete="restrict",
        help="Optional: On the clear advance, the clearing "
        "activity will create default activity line.",
    )

    def _get_activity_advance(self):
        return self.env.ref("budget_activity_advance_clearing.budget_activity_advance")

    @api.onchange("advance")
    def onchange_advance(self):
        """Default activity on advance document"""
        res = super().onchange_advance()
        self.tax_ids = False
        if self.advance:
            self.activity_id = self._get_activity_advance()
        return res
