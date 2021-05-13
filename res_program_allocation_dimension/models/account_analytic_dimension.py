# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountAnalyticDimension(models.Model):
    _inherit = "account.analytic.dimension"

    @api.model
    def get_budget_move_models(self):
        res = super().get_budget_move_models()
        return res + ["fund.constraint"]

    @api.model
    def get_budget_report_models(self):
        res = super().get_budget_report_models()
        return res + ["source.fund.monitor.report"]
