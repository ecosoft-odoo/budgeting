# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class BaseBudgetMove(models.AbstractModel):
    _inherit = "base.budget.move"

    department_id = fields.Many2one(
        comodel_name="hr.department",
        compute="_compute_department_id",
        store=True,
    )

    @api.depends(
        "analytic_account_id.department_id",
        "analytic_account_id.project_id.department_id",
    )
    def _compute_department_id(self):
        """Find department from department analytic or department project"""
        for rec in self:
            rec.department_id = (
                rec.analytic_account_id.department_id
                or rec.analytic_account_id.project_id.department_id
            )
