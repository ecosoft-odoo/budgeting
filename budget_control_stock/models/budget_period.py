# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BudgetPeriod(models.Model):
    _inherit = "budget.period"

    stock = fields.Boolean(
        string="On Stock",
        compute="_compute_control_stock",
        store=True,
        readonly=False,
        help="Control budget on stock picking confirmed/validated",
    )

    def _budget_info_query(self):
        query = super()._budget_info_query()
        query["info_cols"]["amount_stock"] = ("75_st_commit", True)
        return query

    @api.depends("control_budget")
    def _compute_control_stock(self):
        for rec in self:
            rec.stock = rec.control_budget

    @api.model
    def _get_eligible_budget_period(self, date=False, doc_type=False):
        budget_period = super()._get_eligible_budget_period(date, doc_type)
        # Get period control budget.
        # if doctype is stock, check special control too.
        if doc_type == "stock":
            return budget_period.filtered(
                lambda bp: (bp.control_budget and bp.stock)
                or (not bp.control_budget and bp.stock)
            )
        return budget_period
