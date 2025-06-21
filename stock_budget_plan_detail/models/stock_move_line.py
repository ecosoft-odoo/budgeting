# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models


class StockMoveLine(models.Model):
    _name = "stock.move.line"
    _inherit = [
        "analytic.dimension.line",
        "stock.move.line",
        "budget.docline.mixin.base",
    ]

    analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        string="Analytic Tags",
    )

    @api.model
    def _prepare_stock_move_vals(self):
        """
        In the case move lines are created manually, we should fill in the
        new move created here with the fund if filled in.
        """
        res = super()._prepare_stock_move_vals()
        if self.fund_id:
            res.update({"fund_id": self.fund_id.id})
        if self.analytic_tag_ids:
            res.update({"analytic_tag_ids": [Command.set(self.analytic_tag_ids.ids)]})
        return res
