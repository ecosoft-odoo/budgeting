# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class SaleOrderLine(models.Model):
    _name = "sale.order.line"
    _inherit = ["analytic.dimension.line", "sale.order.line"]
    _analytic_tag_field_name = "analytic_tag_ids"
    
    @api.depends("order_id", "order_id.account_analytic_id")
    def _compute_analytic_tag_all(self):
        for doc in self:
            analytic_tag_ids = doc.order_id.account_analytic_id.allocation_line_ids.mapped(doc._analytic_tag_field_name)
            doc.analytic_tag_all = analytic_tag_ids
