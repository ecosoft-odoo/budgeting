# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HRExpense(models.Model):
    _name = "hr.expense"
    _inherit = ["analytic.dimension.line", "hr.expense"]
    _analytic_tag_field_name = "analytic_tag_ids"

    analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        domain=lambda self: self._domain_analytic_tag(),
    )

    def _domain_analytic_tag(self):
        """Overwrite domain from core odoo"""
        domain = "[('id', 'in', analytic_tag_all or []), '|', \
            ('id', 'in', domain_tag_ids or []), \
            ('analytic_dimension_id.by_sequence', '=', False), '|', \
            ('company_id', '=', False), ('company_id', '=', company_id)]"
        return domain

    def _get_account_move_line_values(self):
        """Update fund in move lines"""
        move_line_values_by_expense = super()._get_account_move_line_values()
        for expense in self:
            fund_dict = {"fund_id": expense.fund_id.id}
            for ml in move_line_values_by_expense[expense.id]:
                if ml.get("product_id", False):
                    ml.update(fund_dict)
        return move_line_values_by_expense
