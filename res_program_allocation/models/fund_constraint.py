# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class FundConstraint(models.Model):
    _inherit = "fund.constraint"

    program_id = fields.Many2one(
        comodel_name="res.program",
        required=True,
    )
    program_allocation_id = fields.Many2one(
        comodel_name="res.program.allocation",
        ondelete="cascade",
    )
    period_id = fields.Many2one(
        comodel_name="budget.period",
        related="program_allocation_id.budget_period_id",
        string="Period",
        help="Period is related from program allocation",
    )
    name = fields.Char(
        compute="_compute_name",
        readonly=False,
        store=True,
    )

    @api.depends("program_id")
    def _compute_name(self):
        for rec in self:
            rec.name = rec.program_id.name or False
