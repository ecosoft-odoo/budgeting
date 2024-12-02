# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class RequestBudgetMove(models.Model):
    _inherit = "request.budget.move"

    expense_request_line_id = fields.Many2one(
        comodel_name="request.document.expense.line",
        readonly=True,
        index=True,
    )
