# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PurchaseRequestBudgetMove(models.Model):
    _inherit = "purchase.request.budget.move"

    sheet_id = fields.Many2one(
        comodel_name="hr.expense.sheet",
        related="expense_id.sheet_id",
    )
    expense_id = fields.Many2one(
        comodel_name="hr.expense",
        readonly=True,
        index=True,
        help="Uncommit budget from this purchase_line_id",
    )
