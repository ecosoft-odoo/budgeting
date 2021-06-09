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

    def _get_budget_allocation_line(self):
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
        source_lines, target_lines = self._get_budget_allocation_line()
        if not (source_lines and target_lines):
            raise UserError(_("Not found related budget allocation lines!"))

    def transfer(self):
        res = super().transfer()
        for transfer in self:
            source_lines, target_lines = transfer._get_budget_allocation_line()
            transfer_amount = transfer.amount
            # Transfer amount more than budget allocation per line
            for i, ba_line in enumerate(source_lines):
                if ba_line.released_amount < transfer.amount:
                    transfer_amount -= ba_line.released_amount
                    ba_line.released_amount -= transfer.amount
                    ba_line.transfered_amount -= transfer.amount
                else:
                    ba_line.released_amount -= transfer_amount
                    ba_line.transfered_amount -= transfer.amount
                if i > 0:
                    source_lines[i - 1] = 0.0
            target_lines[0].released_amount += transfer.amount
            target_lines[0].transfered_amount += transfer.amount
        return res
