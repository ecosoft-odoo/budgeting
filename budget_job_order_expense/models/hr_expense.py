# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HRExpense(models.Model):
    _inherit = "hr.expense"

    job_order_id = fields.Many2one(
        readonly=True,
        comodel_name="budget.job.order",
        state={"draft": [("readonly", False)]},
    )

    def _get_account_move_line_values(self):
        move_line_values_by_expense = super()._get_account_move_line_values()
        for expense in self:
            job_order_dict = {"job_order_id": expense.job_order_id.id}
            for ml in move_line_values_by_expense[expense.id]:
                if ml.get("product_id"):
                    ml.update(job_order_dict)
        return move_line_values_by_expense
