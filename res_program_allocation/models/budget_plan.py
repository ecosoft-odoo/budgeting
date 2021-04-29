# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ast

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class BudgetPlan(models.Model):
    _inherit = "budget.plan"

    program_allocation_id = fields.Many2one(
        comodel_name="res.program.allocation",
    )
    init_amount = fields.Monetary(
        string="Initial Amount",
        readonly=True,
        help="Initial amount from Program Allocation",
    )

    def create_revision(self):
        res = super().create_revision()
        new_plan = self.search(ast.literal_eval(res.get("domain", False)))
        new_plan.ensure_one()
        new_plan.program_allocation_id.write({"plan_id": new_plan.id})
        return res

    @api.constrains("state")
    def _check_amount_initial(self):
        prec_digits = self.env.user.company_id.currency_id.decimal_places
        if self.state not in ["draft", "cancel"] and any(
            float_compare(
                rec.init_amount, rec.total_amount, precision_digits=prec_digits
            )
            != 0
            for rec in self
        ):
            raise UserError(_("Total Amount is not equal Initial Amount."))
