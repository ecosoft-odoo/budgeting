# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class StockRequest(models.Model):
    _name = "stock.request"
    _inherit = [
        "analytic.dimension.line",
        "stock.request",
        "budget.docline.mixin.base",
    ]
    _budget_analytic_field = "analytic_account_id"
    _analytic_tag_field_name = "analytic_tag_ids"
