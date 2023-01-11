# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class PurchaseOrderLine(models.Model):
    _name = "purchase.order.line"
    _inherit = ["analytic.dimension.line", "purchase.order.line"]
    __budget_analytic_field = "account_analytic_id"
    _analytic_tag_field_name = "analytic_tag_ids"
