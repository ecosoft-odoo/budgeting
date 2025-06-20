# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, models


class PurchaseOrderLine(models.Model):
    _name = "purchase.order.line"
    _inherit = ["analytic.dimension.line", "purchase.order.line"]

    def _prepare_account_move_line(self, move=False):
        res = super()._prepare_account_move_line(move)
        res["fund_id"] = self.fund_id.id
        return res

    def _init_docline_budget_vals(self, budget_vals, analytic_id):
        self.ensure_one()
        budget_vals = super()._init_docline_budget_vals(budget_vals, analytic_id)
        # Document specific vals
        budget_vals.update(
            {
                "analytic_tag_ids": [Command.set(self.analytic_tag_ids.ids)],
            }
        )
        return super()._init_docline_budget_vals(budget_vals, analytic_id)
