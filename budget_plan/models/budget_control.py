# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    plan_id = fields.Many2one(
        comodel_name="budget.plan",
        index=True,
        ondelete="cascade",
    )
    allocated_amount = fields.Monetary(
        readonly=True,
        help="Total amount from budget plan before revision",
    )
    released_amount = fields.Monetary(
        readonly=True,
        help="Released Amount compute from budget plan.",
    )

    def _update_allocated_amount(self, plan_line):
        for rec in self:
            bc_plan_line = plan_line.filtered(
                lambda l: l.analytic_account_id.id
                == rec.analytic_account_id.id
            )
            if bc_plan_line.allocated_amount != rec.allocated_amount:
                rec.write({"allocated_amount": bc_plan_line.allocated_amount})
