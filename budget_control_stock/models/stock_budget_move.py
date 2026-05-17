# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class StockBudgetMove(models.Model):
    _name = "stock.budget.move"
    _inherit = ["base.budget.move"]
    _description = "Stock Budget Moves (SVL Actual)"

    stock_move_id = fields.Many2one(
        comodel_name="stock.move",
        readonly=True,
        index=True,
        ondelete="cascade",
        help="Source stock.move that produced this budget actual.",
    )
    picking_id = fields.Many2one(
        comodel_name="stock.picking",
        related="stock_move_id.picking_id",
        store=True,
        index=True,
    )
    stock_valuation_layer_ids = fields.Many2many(
        comodel_name="stock.valuation.layer",
        relation="stock_budget_move_svl_rel",
        column1="budget_move_id",
        column2="svl_id",
        readonly=True,
        help="SVL rows summed into this budget actual amount.",
    )

    @api.depends("picking_id")
    def _compute_reference(self):
        for rec in self:
            rec.reference = (
                rec.reference
                if rec.reference
                else (rec.picking_id.display_name or rec.stock_move_id.display_name)
            )
