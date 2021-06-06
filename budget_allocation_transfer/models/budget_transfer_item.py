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
        source_lines = (
            self.source_budget_control_id.sudo().allocation_line_ids.filtered_domain(
                self._get_domain_source_allocation_line()
            )
        )
        target_lines = (
            self.target_budget_control_id.sudo().allocation_line_ids.filtered_domain(
                self._get_domain_target_allocation_line()
            )
        )
        return source_lines, target_lines
    
    def _check_constraint_transfer(self):
        super()._check_constraint_transfer()
        source_lines, target_lines = self._get_budget_allocation_line()
        if not (source_lines and target_lines):
            raise UserError(_("Budget allocation lines with conditions not found!"))

    def transfer(self):
        res = super().transfer()
        for transfer in self:
            source_lines, target_lines = transfer._get_budget_allocation_line()
            transfer_amount = transfer.amount
            # Transfer amount more than budget allocation per line
            for ba_line in source_lines:
                if ba_line.budget_amount < transfer.amount:
                    transfer_amount -= ba_line.budget_amount
                    ba_line.budget_amount = 0.0
                else:
                    ba_line.budget_amount -= transfer_amount
            target_lines[0].budget_amount += transfer.amount
        return res
