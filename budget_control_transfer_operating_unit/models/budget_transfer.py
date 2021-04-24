# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import api, fields, models


class BudgetTransfer(models.Model):
    _inherit = "budget.transfer"

    source_operating_unit = fields.Char(
        string="Operating Unit From",
        compute="_compute_operating_unit_ids",
        compute_sudo=True,
        store=True,
    )
    target_operating_unit = fields.Char(
        string="Operating Unit To",
        compute="_compute_operating_unit_ids",
        compute_sudo=True,
        store=True,
    )
    operating_unit_ids = fields.Many2many(
        comodel_name="operating.unit",
        string="Operating Units",
        relation="budget_transfer_operating_unit_rel",
        compute="_compute_operating_unit_ids",
        compute_sudo=True,
        store=True,
        domain="[('user_ids', '=', uid)]",
        column1="transfer_id",
        column2="operating_unit_id",
    )

    @api.depends(
        "transfer_item_ids.source_operating_unit_id",
        "transfer_item_ids.target_operating_unit_id",
    )
    def _compute_operating_unit_ids(self):
        for rec in self:
            source = rec.transfer_item_ids.mapped("source_operating_unit_id")
            target = rec.transfer_item_ids.mapped("target_operating_unit_id")
            ou = source + target
            rec.operating_unit_ids = ou.ids
            rec.source_operating_unit = ", ".join(source.mapped("name"))
            rec.target_operating_unit = ", ".join(target.mapped("name"))
