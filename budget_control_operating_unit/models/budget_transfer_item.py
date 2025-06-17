# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetTransferItem(models.Model):
    _inherit = "budget.transfer.item"

    operating_unit_from_id = fields.Many2one(
        comodel_name="operating.unit",
        related="budget_control_from_id.operating_unit_id",
        store=True,
        string="Operating Unit From",
    )
    operating_unit_to_id = fields.Many2one(
        comodel_name="operating.unit",
        related="budget_control_to_id.operating_unit_id",
        store=True,
        string="Operating Unit To",
    )
