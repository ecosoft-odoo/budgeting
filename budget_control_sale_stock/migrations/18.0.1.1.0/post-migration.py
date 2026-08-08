# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Convert the SO part of existing allocations and keep manual adjustments."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    controls = env["budget.control"].search([("sale_order_ids", "!=", False)])
    for control in controls:
        old_sale_cost = sum(
            line.purchase_price * line.product_uom_qty
            for order in control.sale_order_ids
            for line in order.order_line
        )
        new_sale_cost = sum(
            order._get_budget_control_allocated_amount()
            for order in control.sale_order_ids
        )
        manual_adjustment = control.allocated_amount - old_sale_cost
        control.allocated_amount = new_sale_cost + manual_adjustment
