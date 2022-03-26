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

    def check_budget_transfer_permission(self):
        source_budget_all_ou = (
            self.env.user.company_id.budget_transfer_source_all_ou
        )
        target_budget_all_ou = (
            self.env.user.company_id.budget_transfer_target_all_ou
        )
        if (
            (
                self._context.get("source_budget", False)
                and source_budget_all_ou
            )
            or (
                self._context.get("target_budget", False)
                and target_budget_all_ou
            )
            or self._context.get("access_sudo", False)
            or self._context.get("from_review_systray", False)
        ):  # support with tier validation
            return True
        return False

    def _read(self, fields):
        """ Add permission to read difference operating unit. """
        if self.check_budget_transfer_permission():
            self = self.sudo().with_context(force_all_ou=1)
        return super()._read(fields)

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
