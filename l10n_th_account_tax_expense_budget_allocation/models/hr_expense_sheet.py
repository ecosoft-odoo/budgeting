# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def _prepare_withholding_tax_entry(self):
        move_vals = super()._prepare_withholding_tax_entry()
        move_vals["not_affect_budget"] = True
        return move_vals

    def _get_move_line_wht_vals(self, deduction, wht_move_lines):
        wht_vals = super()._get_move_line_wht_vals(deduction, wht_move_lines)
        wht_vals.update(
            {
                "analytic_account_id": wht_move_lines.analytic_account_id.id,
                "analytic_tag_ids": [(6, 0, wht_move_lines.analytic_tag_ids.ids)]
                if wht_move_lines.analytic_tag_ids
                else [],
                "fund_id": wht_move_lines.fund_id.id,
            }
        )
        return wht_vals
