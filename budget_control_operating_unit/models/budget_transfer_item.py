# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetTransferItem(models.Model):
    _inherit = "budget.transfer.item"

    source_operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        related="source_budget_control_id.operating_unit_id",
        string="Source Operating Unit",
        store=True,
        index=True,
    )
    target_operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        related="target_budget_control_id.operating_unit_id",
        string="Target Operating Unit",
        store=True,
        index=True,
    )

    # def _read(self, fields):
    #     """ Add permission to read difference operating unit. """
    #     if self._context.get("access_sudo", False):
    #         self = self.sudo()
    #     return super()._read(fields)

    def _get_budget_control_transfer(self):
        """ Make sure that user can see available with other OU """
        return super(
            BudgetTransferItem, self.with_context(force_all_ou=1)
        )._get_budget_control_transfer()

    def transfer(self):
        """ Make sure that user can transfer with other OU """
        return super(BudgetTransferItem, self.sudo()).transfer()

    def reverse(self):
        """ Make sure that user can reverse with other OU """
        return super(BudgetTransferItem, self.sudo()).reverse()
