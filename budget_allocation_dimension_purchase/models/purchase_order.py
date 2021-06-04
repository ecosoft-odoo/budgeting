# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class PurchaseOrderLine(models.Model):
    _name = "purchase.order.line"
    _inherit = ["analytic.dimension.line", "purchase.order.line"]
    _analytic_tag_field_name = "analytic_tag_ids"
    _amount_balance_field = "price_total"

    # Trigger analytic
    @api.depends("account_analytic_id")
    def _compute_analytic_tag_all(self):
        super()._compute_analytic_tag_all()
