# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class FundConstraint(models.Model):
    _name = "fund.constraint"
    _inherit = ["analytic.dimension.line", "fund.constraint"]
    _analytic_tag_field_name = "analytic_tag_ids"

    analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        string="Analytic Tags",
    )
    program_id = fields.Many2one(
        comodel_name="res.program",
        required=False,
        ondelete="restrict",
    )

    @api.depends("analytic_account_id")
    def _compute_name(self):
        for rec in self:
            rec.name = rec.analytic_account_id.name or False
