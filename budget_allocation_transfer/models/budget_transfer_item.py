# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError


class BudgetTransferItem(models.Model):
    _inherit = "budget.transfer.item"

    def _get_domain_source_allocation_line(self):
        return []

    def _get_domain_target_allocation_line(self):
        return []

    def _get_budget_allocation_lines(self):
        """ bypass permission admin for find budget allocation line """
        source_ba_line = (
            self.source_budget_control_id.sudo().allocation_line_ids
        )
        target_ba_line = (
            self.target_budget_control_id.sudo().allocation_line_ids
        )
        source_lines = source_ba_line.filtered_domain(
            self._get_domain_source_allocation_line()
        )
        target_lines = target_ba_line.filtered_domain(
            self._get_domain_target_allocation_line()
        )
        return source_lines, target_lines

    def _check_constraint_transfer(self):
        super()._check_constraint_transfer()
        source_lines, target_lines = self._get_budget_allocation_lines()
        if not (source_lines and target_lines):
            raise UserError(_("Not found related budget allocation lines!"))

    def _get_message_source_transfer(self):
        return "Source Budget: {}".format(self.source_budget_control_id.name)

    def _get_message_target_transfer(self):
        return "Target Budget: {}".format(self.target_budget_control_id.name)

    def transfer(self):
        res = super().transfer()
        for transfer in self:
            (
                source_lines,
                target_lines,
            ) = transfer._get_budget_allocation_lines()
            transfer_amount = transfer.amount
            # Transfer amount more than budget allocation per line
            for ba_line in source_lines:
                if ba_line.released_amount < transfer_amount:
                    transfer_amount -= ba_line.released_amount
                    ba_line.released_amount = 0.0
                else:
                    ba_line.released_amount -= transfer_amount
            target_lines[0].released_amount += transfer_amount
            # Log message to budget allocation
            allocation_lines = source_lines + target_lines
            budget_allocation_ids = allocation_lines.mapped(
                "budget_allocation_id"
            )
            message = _(
                "{}<br/><b>transfer to</b><br/>{}<br/>with amount {:,.2f} {}".format(
                    transfer._get_message_source_transfer(),
                    transfer._get_message_target_transfer(),
                    transfer.amount,
                    self.env.company.currency_id.symbol,
                )
            )
            budget_allocation_ids.message_post(body=message)

        return res

    def reverse(self):
        res = super().reverse()
        for transfer in self:
            (
                source_lines,
                target_lines,
            ) = transfer._get_budget_allocation_lines()
            reverse_amount = transfer.amount
            # Update release amount
            source_lines[0].released_amount += reverse_amount
            target_lines[0].released_amount -= reverse_amount
            # Log message to budget allocation
            allocation_lines = source_lines + target_lines
            budget_allocation_ids = allocation_lines.mapped(
                "budget_allocation_id"
            )
            message = _(
                "{}<br/><b>reverse from</b><br/>{}<br/>with amount {:,.2f} {}".format(
                    transfer._get_message_source_transfer(),
                    transfer._get_message_target_transfer(),
                    transfer.amount,
                    self.env.company.currency_id.symbol,
                )
            )
            budget_allocation_ids.message_post(body=message)

        return res
