# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models


class PurchaseGuarantee(models.Model):
    _inherit = "purchase.guarantee"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        compute="_compute_operating_unit",
        index=True,
    )

    @api.depends("reference")
    def _compute_operating_unit(self):
        for rec in self:
            rec.operating_unit_id = (
                rec.reference and rec.reference.operating_unit_id or False
            )
