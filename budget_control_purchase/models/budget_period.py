# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BudgetPeriod(models.Model):
    _inherit = "budget.period"

    purchase = fields.Boolean(
        string="On Purchase",
        compute="_compute_control_purchase",
        store=True,
        readonly=False,
        help="Control budget on purchase order confirmation",
    )

    def _budget_info_query(self):
        query = super()._budget_info_query()
        query["info_cols"]["amount_purchase"] = ("30_po_commit", True)
        return query

    @api.depends("control_budget")
    def _compute_control_purchase(self):
        for rec in self:
            rec.purchase = rec.control_budget

    @api.model
    def _get_eligible_budget_period(self, date=False, doc_type=False):
        budget_period = super()._get_eligible_budget_period(date, doc_type)
        # Get period control budget.
        # if doctype is purchase, check special control too.
        if doc_type == "purchase":
            return budget_period.filtered(
                lambda bp: (bp.control_budget and bp.purchase)
                or (not bp.control_budget and bp.purchase)
            )
        return budget_period

    @api.model
    def check_budget_precommit(self, doclines, doc_type="account"):
        """This function add for the extension module can
        call this function to precommit check budget"""
        budget_moves = False
        if doc_type == "purchase":
            budget_moves = doclines.with_context(
                force_commit=True
            ).uncommit_purchase_request_budget()
        res = super().check_budget_precommit(doclines, doc_type=doc_type)
        if budget_moves:
            budget_moves.unlink()
        return res
