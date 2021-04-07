# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    allocated_amount = fields.Monetary(
        readonly=True,
        help="Total amount from budget plan before revision",
    )
    released_amount = fields.Monetary(
        readonly=True,
        help="Released Amount compute from budget plan.",
    )

    def _update_allocated_amount(self, plan_line):
        alloc = {
            x.analytic_account_id.id: x.allocated_amount for x in plan_line
        }
        for rec in self:
            rec.action_draft()
            rec.allocated_amount = alloc.get(rec.analytic_account_id.id)
