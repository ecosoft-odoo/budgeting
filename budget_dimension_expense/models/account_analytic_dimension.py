# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountAnalyticDimension(models.Model):
    _inherit = "account.analytic.dimension"

    @api.model
    def get_budget_move_models(self):
        return super().get_budget_move_models() + ["expense.budget.move"]

    @api.model
    def get_model_names(self):
        return super().get_model_names() + ["hr.expense"]
