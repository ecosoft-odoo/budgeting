# Copyright 2013 Julius Network Solutions
# Copyright 2015 Clear Corp
# Copyright 2016 OpenSynergy Indonesia
# Copyright 2017 ForgeFlow S.L.
# Copyright 2018 Hibou Corp.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        string="Fund",
        index=True,
    )

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
                # Add fund in debit line
                if self.fund_id:
                    line[2].update({"fund_id": self.fund_id.id})
        return res

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        fields = super()._prepare_merge_moves_distinct_fields()
        fields.append("fund_id")
        return fields


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    fund_id = fields.Many2one(related="move_id.fund_id")
