# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BudgetPeriod(models.Model):
    _inherit = "budget.period"

    request_document = fields.Boolean(
        string="On Request Document",
        compute="_compute_control_request_document",
        store=True,
        readonly=False,
        help="Control budget on expense approved",
    )

    def _budget_info_query(self):
        query = super()._budget_info_query()
        query["info_cols"]["amount_request"] = ("15_rq_commit", True)
        return query

    @api.depends("control_budget")
    def _compute_control_request_document(self):
        for rec in self:
            rec.request_document = rec.control_budget

    @api.model
    def _prepare_controls(self, budget_period, doclines):
        if doclines.env.context.get("alt_budget_move_model") == "request.budget.move":
            doclines = doclines[doclines._doc_rel].request_document_id
        return super()._prepare_controls(budget_period, doclines)

    @api.model
    def _get_eligible_budget_period(self, date=False, doc_type=False):
        budget_period = super()._get_eligible_budget_period(date, doc_type)
        # Get period control budget.
        # if doctype is request, check special control too.
        if doc_type == "request":
            return budget_period.filtered(
                lambda bp: (bp.control_budget and bp.request_document)
                or (not bp.control_budget and bp.request_document)
            )
        return budget_period
