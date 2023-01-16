# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class PurchaseRequestLine(models.Model):
    _name = "purchase.request.line"
    _inherit = ["analytic.dimension.line", "purchase.request.line"]
    _budget_analytic_field = "analytic_account_id"
    _analytic_tag_field_name = "analytic_tag_ids"
