# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class StockBudgetMove(models.Model):
    _name = "stock.budget.move"
    _inherit = ["base.budget.move"]
    _description = "Stock Budget Moves"

    move_id = fields.Many2one(
        comodel_name="stock.move",
        readonly=True,
        index=True,
        help="Commit budget for this stock.move",
    )
    picking_id = fields.Many2one(
        comodel_name="stock.picking",
        related="move_id.picking_id",
        readonly=True,
        store=True,
        index=True,
        ondelete="cascade",
    )
    account_move_id = fields.Many2one(
        comodel_name="account.move",
        related="account_move_line_id.move_id",
        store=True,
    )
    account_move_line_id = fields.Many2one(
        comodel_name="account.move.line",
        readonly=True,
        index=True,
        help="Uncommit budget from this account.move.line",
    )

    @api.depends("picking_id")
    def _compute_reference(self):
        for rec in self:
            rec.reference = (
                rec.reference if rec.reference else rec.picking_id.display_name
            )

    @api.depends("picking_id")
    def _compute_source_document(self):
        res = super()._compute_source_document()
        for rec in self.filtered("picking_id"):
            if not rec.source_document:
                rec.source_document = rec.picking_id.origin or False
        return res
