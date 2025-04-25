# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, fields, models


class HRExpense(models.Model):
    _name = "hr.expense"
    _inherit = ["analytic.dimension.line", "hr.expense"]

    # Overwrite analytic_tag_ids field for add
    analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        domain=lambda self: self._domain_analytic_tag(),
    )

    def _domain_analytic_tag(self):
        """Overwrite domain from core odoo"""
        domain = """[
            ('id', 'in', analytic_tag_all or []),
            '|',
            ('id', 'in', domain_tag_ids or []),
            ('analytic_dimension_id.by_sequence', '=', False)
        ]
        """
        return domain

    def _prepare_move_lines_vals(self):
        vals = super()._prepare_move_lines_vals()
        if self.fund_id:
            vals.update({"fund_id": self.fund_id.id})
        return vals

    def _init_docline_budget_vals(self, budget_vals, analytic_id):
        self.ensure_one()
        budget_vals = super()._init_docline_budget_vals(budget_vals, analytic_id)
        # Document specific vals
        budget_vals.update(
            {
                "analytic_tag_ids": [Command.set(self.analytic_tag_ids.ids)],
            }
        )
        return super()._init_docline_budget_vals(budget_vals, analytic_id)
