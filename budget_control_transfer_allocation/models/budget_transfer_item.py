# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError


class BudgetTransferItem(models.Model):
    _inherit = "budget.transfer.item"

    @api.depends("source_budget_control_id", "target_budget_control_id")
    def _compute_amount_available(self):
        for transfer in self:
            source_budget_ctrl = transfer.source_budget_control_id
            target_budget_ctrl = transfer.target_budget_control_id
            transfer.source_amount_available = (
                source_budget_ctrl.released_amount
            )
            transfer.target_amount_available = (
                target_budget_ctrl.released_amount
            )

    def transfer(self):
        for transfer in self:
            if transfer.state != "draft":
                raise ValidationError(_("Invalid state!"))
            if (
                transfer.source_budget_control_id
                == transfer.target_budget_control_id
            ):
                raise UserError(
                    _(
                        "You can not transfer from the same budget control sheet!"
                    )
                )
            if transfer.amount < 0.0:
                raise UserError(_("Transfer amount must be positive!"))
            transfer.source_budget_control_id.released_amount -= (
                transfer.amount
            )
            transfer.target_budget_control_id.released_amount += (
                transfer.amount
            )
            transfer.state = "transfer"
        # Final check
        source_amounts = self.mapped(
            "source_budget_control_id.released_amount"
        )
        if list(filter(lambda a: a < 0, source_amounts)):
            raise ValidationError(_("Negative source amount after transfer!"))

    def reverse(self):
        for transfer in self:
            if transfer.state != "transfer":
                raise ValidationError(_("Invalid state!"))
            transfer.source_budget_control_id.released_amount += (
                transfer.amount
            )
            transfer.target_budget_control_id.released_amount -= (
                transfer.amount
            )
