# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    def recompute_budget_move(self):
        res = super().recompute_budget_move()
        for pr_line in self:
            pr_line.request_id.expense_sheet_ids.mapped(
                "expense_line_ids"
            ).uncommit_purchase_request_budget()
        return res
