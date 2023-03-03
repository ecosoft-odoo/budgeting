# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import api, models


class AccountAnalyticDimension(models.Model):
    _inherit = "account.analytic.dimension"

    @api.model
    def get_model_names(self):
        res = super().get_model_names()
        return res + ["stock.move", "stock.move.line", "stock.scrap"]
