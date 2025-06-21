# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, fields, models


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = [
        "analytic.dimension.line",
        "stock.move",
        "budget.docline.mixin.base",
    ]

    analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        string="Analytic Tags",
    )

    def _prepare_account_move_line(
        self, qty, cost, credit_account_id, debit_account_id, svl_id, description
    ):
        self.ensure_one()
        res = super()._prepare_account_move_line(
            qty, cost, credit_account_id, debit_account_id, svl_id, description
        )
        for line in res:
            if (
                line[2]["account_id"]
                != self.product_id.categ_id.property_stock_valuation_account_id.id
            ):
                # Add fund, analytic tags in debit line
                line[2].update(
                    {
                        "fund_id": self.fund_id.id,
                        "analytic_tag_ids": [Command.set(self.analytic_tag_ids.ids)],
                    },
                )
        return res

    def _prepare_procurement_values(self):
        """
        Allows to transmit fund, analytic tags from moves to new
        moves through procurement.
        """
        res = super()._prepare_procurement_values()
        if self.fund_id:
            res.update({"fund_id": self.fund_id.id})
        if self.analytic_tag_ids:
            res.update({"analytic_tag_ids": [Command.set(self.analytic_tag_ids.ids)]})
        return res

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        """
        We fill in the fund, analytic tags when creating the move line from the move
        """
        res = super()._prepare_move_line_vals(
            quantity=quantity, reserved_quant=reserved_quant
        )
        if self.fund_id:
            res.update({"fund_id": self.fund_id.id})
        if self.analytic_tag_ids:
            res.update({"analytic_tag_ids": [Command.set(self.analytic_tag_ids.ids)]})
        return res

    def _prepare_account_move_vals(
        self,
        credit_account_id,
        debit_account_id,
        journal_id,
        qty,
        description,
        svl_id,
        cost,
    ):
        """Not affect budget"""
        self.ensure_one()
        move_vals = super()._prepare_account_move_vals(
            credit_account_id,
            debit_account_id,
            journal_id,
            qty,
            description,
            svl_id,
            cost,
        )
        move_vals["not_affect_budget"] = True
        return move_vals
