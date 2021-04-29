# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    program_ids = fields.Many2many(
        comodel_name="res.program",
        relation="budget_control_res_program_rel",
        column1="budget_control_id",
        column2="program_id",
        compute="_compute_program",
    )

    @api.depends("analytic_account_id")
    def _compute_program(self):
        for rec in self:
            rec.program_ids = rec.fund_constraint_ids.mapped("program_id")
