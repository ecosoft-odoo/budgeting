# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrExpense(models.Model):
    _name = "hr.expense"
    _inherit = ["analytic.dimension.line", "hr.expense"]
    _analytic_tag_field_name = "analytic_tag_ids"

    analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        domain=lambda self: self._domain_analytic_tag(),
    )

    def _domain_analytic_tag(self):
        domain = """[
            ('id', 'in', analytic_tag_all or []),
            '|', ('id', 'in', domain_tag_ids or []),
            ('analytic_dimension_id.by_sequence', '=', False),
            '|', ('company_id', '=', False), ('company_id', '=', company_id)
        ]"""
        return domain

    def _get_account_move_line_values(self):
        move_line_values_by_expense = super()._get_account_move_line_values()
        for expense in self:
            for ml in move_line_values_by_expense[expense.id]:
                if not ml.get("product_id", False):
                    ml.update({"exclude_from_invoice_tab": True})
        return move_line_values_by_expense

    # Trigger analytic
    @api.depends("analytic_account_id")
    def _compute_analytic_tag_all(self):
        super()._compute_analytic_tag_all()
