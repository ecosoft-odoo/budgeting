# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetTransferItem(models.Model):
    _inherit = "budget.transfer.item"

    source_operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        related="source_budget_control_id.operating_unit_id",
        string="Source Operating Unit",
        compute_sudo=True,
        store=True,
        index=True,
    )
    target_operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        related="target_budget_control_id.operating_unit_id",
        string="Target Operating Unit",
        compute_sudo=True,
        store=True,
        index=True,
    )
