# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"
    _docline_rel = "move_ids"
    _docline_type = "stock"

    budget_move_ids = fields.One2many(
        comodel_name="stock.budget.move",
        inverse_name="picking_id",
        string="Stock Budget Moves",
    )

    def action_view_budget_moves(self):
        self.ensure_one()
        return {
            "name": self.env._("Stock Budget Moves"),
            "type": "ir.actions.act_window",
            "res_model": "stock.budget.move",
            "view_mode": "list,form",
            "domain": [("picking_id", "=", self.id)],
        }
