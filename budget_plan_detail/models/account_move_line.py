# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

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
