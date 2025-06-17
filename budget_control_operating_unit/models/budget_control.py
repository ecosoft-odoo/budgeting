# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class BudgetControl(models.Model):
    _inherit = "budget.control"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        compute="_compute_budget_operating_unit",
        store=True,
    )

    @api.depends("analytic_account_id.operating_unit_ids")
    def _compute_budget_operating_unit(self):
        """Operating Unit can selected 1 only for analytic account"""
        for rec in self:
            if len(rec.analytic_account_id.operating_unit_ids) > 1:
                raise UserError(
                    self.env._("Analytic Account can't select operating unit > 1")
                )
            rec.operating_unit_id = rec.analytic_account_id.operating_unit_ids.id
