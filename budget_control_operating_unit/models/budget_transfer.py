# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BudgetTransfer(models.Model):
    _inherit = "budget.transfer"

    operating_unit_from = fields.Char(
        compute="_compute_operating_unit_ids",
        store=True,
    )
    operating_unit_to = fields.Char(
        compute="_compute_operating_unit_ids",
        store=True,
    )
    operating_unit_ids = fields.Many2many(
        comodel_name="operating.unit",
        relation="budget_transfer_operating_unit_rel",
        column1="transfer_id",
        column2="operating_unit_id",
        string="Operating Units",
        compute="_compute_operating_unit_ids",
        store=True,
    )

    @api.depends(
        "transfer_item_ids.operating_unit_from_id",
        "transfer_item_ids.operating_unit_to_id",
    )
    def _compute_operating_unit_ids(self):
        for rec in self.sudo():
            ou_from = rec.transfer_item_ids.mapped("operating_unit_from_id")
            ou_to = rec.transfer_item_ids.mapped("operating_unit_to_id")
            rec.operating_unit_ids = (ou_from + ou_to).ids
            rec.operating_unit_from = ", ".join(ou_from.mapped("name"))
            rec.operating_unit_to = ", ".join(ou_to.mapped("name"))
