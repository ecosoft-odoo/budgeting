# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class HrExpense(models.Model):
    _name = "hr.expense"
    _inherit = ["analytic.dimension.line", "hr.expense"]
    _analytic_tag_field_name = "analytic_tag_ids"
    _amount_balance_field = "total_amount"

    # Trigger analytic
    @api.depends("analytic_account_id")
    def _compute_analytic_tag_all(self):
        super()._compute_analytic_tag_all()
