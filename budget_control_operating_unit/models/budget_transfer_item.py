# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetTransferItem(models.Model):
    _inherit = "budget.transfer.item"

    operating_unit_from_id = fields.Many2one(
        comodel_name="operating.unit",
        related="budget_control_from_id.operating_unit_id",
        string="Operating Unit From",
        store=True,
        index=True,
    )
    operating_unit_to_id = fields.Many2one(
        comodel_name="operating.unit",
        related="budget_control_to_id.operating_unit_id",
        string="Operating Unit To",
        store=True,
        index=True,
    )

    def _get_budget_control_transfer(self):
        """Make sure that user can see available with other OU"""
        return super(
            BudgetTransferItem, self.with_context(force_all_ou=1)
        )._get_budget_control_transfer()
