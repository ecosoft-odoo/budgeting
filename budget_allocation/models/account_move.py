# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        """ Check commitment From Budget Allocation """
        res = super().action_post()
        for doc in self:
            doc.budget_move_ids.check_budget_constraint(doc.invoice_line_ids)
        return res
