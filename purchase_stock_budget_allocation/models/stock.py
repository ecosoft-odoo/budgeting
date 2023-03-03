# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = [
        "analytic.dimension.line",
        "stock.move",
        "budget.docline.mixin.base",
    ]
    _budget_analytic_field = "analytic_account_id"
    _analytic_tag_field_name = "analytic_tag_ids"

    def _prepare_account_move_line(
        self, qty, cost, credit_account_id, debit_account_id, description
    ):
        self.ensure_one()
        res = super()._prepare_account_move_line(
            qty, cost, credit_account_id, debit_account_id, description
        )
        for line in res:
            if (
                line[2]["account_id"]
                != self.product_id.categ_id.property_stock_valuation_account_id.id
            ):
                # Add analytic account in debit line
                if self.fund_id:
                    line[2].update({"fund_id": self.fund_id.id})
        return res

    def _prepare_procurement_values(self):
        """
        Allows to transmit fund from moves to new
        moves through procurement.
        """
        res = super()._prepare_procurement_values()
        if self.fund_id:
            res.update({"fund_id": self.fund_id.id})
        return res

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        fields = super()._prepare_merge_moves_distinct_fields()
        fields.append("fund_id")
        return fields

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        """
        We fill in the fund when creating the move line from the move
        """
        res = super()._prepare_move_line_vals(
            quantity=quantity, reserved_quant=reserved_quant
        )
        if self.fund_id:
            res.update({"fund_id": self.fund_id.id})
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


class StockMoveLine(models.Model):
    _name = "stock.move.line"
    _inherit = [
        "analytic.dimension.line",
        "stock.move.line",
        "budget.docline.mixin.base",
    ]
    _budget_analytic_field = "analytic_account_id"
    _analytic_tag_field_name = "analytic_tag_ids"

    @api.model
    def _prepare_stock_move_vals(self):
        """
        In the case move lines are created manually, we should fill in the
        new move created here with the fund if filled in.
        """
        res = super()._prepare_stock_move_vals()
        if self.fund_id:
            res.update({"fund_id": self.fund_id.id})
        return res
