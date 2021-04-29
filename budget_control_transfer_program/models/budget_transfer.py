# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetTransfer(models.Model):
    _inherit = "budget.transfer"

    def _check_fund_constraint_ids(self):
        """Ensure budget control transfer from program only."""
        transfers = self.mapped("transfer_item_ids")
        transfers._check_fund_constraint_ids()

    def action_submit(self):
        self._check_fund_constraint_ids()
        return super().action_submit()
