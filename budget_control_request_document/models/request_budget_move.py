# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class RequestBudgetMove(models.Model):
    _name = "request.budget.move"
    _inherit = ["base.budget.move"]
    _description = "Request Budget Moves"

    request_id = fields.Many2one(
        comodel_name="request.request",
        related="request_document_id.request_id",
        store=True,
        index=True,
        help="Commit budget for this request_document_id",
    )
    request_document_id = fields.Many2one(
        comodel_name="request.document",
        index=True,
        help="Commit budget for this request_id",
    )

    @api.depends("request_document_id")
    def _compute_reference(self):
        for rec in self:
            rec.reference = (
                rec.reference if rec.reference else rec.request_document_id.display_name
            )
