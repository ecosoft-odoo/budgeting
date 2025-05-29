# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountAnalyticDimension(models.Model):
    _inherit = "account.analytic.dimension"

    @api.model
    def get_model_names(self):
        res = super().get_model_names()
        # All models that have budget.move in it
        budget_move_models = (
            self.env["ir.model"]
            .sudo()
            .search(
                [("model", "like", "%.budget.move")],
            )
            .mapped("model")
        )
        # Extra models
        extra_models = [
            "budget.plan.line.detail",
            "budget.move.adjustment.item",
            "budget.monitor.report",
            "budget.source.fund.report",
        ]
        return res + budget_move_models + extra_models
