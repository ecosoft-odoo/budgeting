# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    def make_purchase_order(self):
        res = super().make_purchase_order()
        if res.get("domain"):
            purchase_id = res.get("domain")[0][2]
            purchase = self.env["purchase.order"].browse(list(set(purchase_id)))
            if purchase.state in ("purchase", "done"):
                purchase.recompute_budget_move()
                requests = self.item_ids.mapped("line_id.request_id")
                requests.recompute_budget_move()
        return res

    @api.model
    def _prepare_purchase_order_line(self, po, item):
        vals = super()._prepare_purchase_order_line(po, item)
        if vals.get("account_analytic_id") and item.line_id.fwd_analytic_account_id:
            vals["account_analytic_id"] = item.line_id.fwd_analytic_account_id.id
        # Check if date_commit is not in the fiscal year, then update it
        fy_dates = item.line_id.company_id.compute_fiscalyear_dates(
            fields.Date.context_today(self)
        )
        if item.line_id.date_commit > fy_dates["date_to"]:
            vals["date_commit"] = item.line_id.date_commit
        return vals

    @api.model
    def _get_order_line_search_domain(self, order, item):
        order_line_data = super()._get_order_line_search_domain(order, item)
        order_line_data.append(("date_commit", "=", item.line_id.date_commit))
        return order_line_data
