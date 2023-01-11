# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountAnalyticDimension(models.Model):
    _inherit = "account.analytic.dimension"

    @api.model
    def get_model_names(self):
        res = super().get_model_names()
        return res + [
            "budget.allocation.line",
            "account.budget.move",
            "budget.move.adjustment.item",
            "budget.monitor.report",
            "budget.source.fund.report",
        ]
