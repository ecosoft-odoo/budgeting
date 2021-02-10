# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import fields, models


class BudgetTransferItem(models.Model):
    _inherit = "budget.transfer.item"

    target_operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        related="transfer_id.operating_unit_id",
    )
    target_budget_control_id = fields.Many2one(
        comodel_name="budget.control",
        domain="[('budget_id', '=', mis_budget_id), "
        "('operating_unit_id', '=', target_operating_unit_id)]",
    )
