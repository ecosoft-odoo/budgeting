# Copyright 2026 Ecosoft Co., Ltd. (<http://ecosoft.co.th>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    sale_order_ids = fields.Many2many(
        comodel_name="sale.order",
        relation="budget_control_sale_order_rel",
        column1="budget_control_id",
        column2="sale_order_id",
        string="Sale Orders",
        copy=False,
    )
    sale_order_count = fields.Integer(compute="_compute_sale_order_count")
    sale_price = fields.Monetary(
        string="Sales Untaxed",
        compute="_compute_sale_fields",
        store=True,
    )
    gross_profit = fields.Monetary(
        compute="_compute_sale_fields",
        store=True,
    )
    gross_profit_percent = fields.Float(
        compute="_compute_sale_fields",
        store=True,
    )

    @api.depends("sale_order_ids")
    def _compute_sale_order_count(self):
        for rec in self:
            rec.sale_order_count = len(rec.sale_order_ids)

    @api.depends(
        "sale_order_ids.amount_untaxed",
        "sale_order_ids.currency_id",
        "sale_order_ids.company_id.currency_id",
        "sale_order_ids.date_order",
        "allocated_amount",
    )
    def _compute_sale_fields(self):
        for rec in self:
            sale_price = sum(
                order._get_budget_control_sale_amount() for order in rec.sale_order_ids
            )
            profit = sale_price - rec.allocated_amount
            rec.sale_price = sale_price
            rec.gross_profit = profit
            rec.gross_profit_percent = (
                (profit / sale_price * 100) if sale_price else 0.0
            )

    def action_open_sale_order(self):
        self.ensure_one()
        return {
            "name": self.env._("Sale Orders"),
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "view_mode": "list,form",
            "domain": [("id", "in", self.sale_order_ids.ids)],
        }
