# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.tools import float_compare


class BudgetControl(models.Model):
    _inherit = "budget.control"

    amount_rolling = fields.Monetary(
        string="Rolling Amount",
        compute="_compute_amount_rolling",
        store=True,
        help="Rolling = Released amount - Consumed + Past Plan",
    )

    @api.depends("item_ids", "released_amount", "amount_consumed")
    def _compute_amount_rolling(self):
        today = fields.Date.context_today(self)
        first_month_day = today.replace(day=1)
        for rec in self:
            item_ids = rec.item_ids.filtered(lambda x: x.date_from < first_month_day)
            amount_past_plan = sum(item_ids.mapped("amount"))
            rec.amount_rolling = (
                rec.released_amount - rec.amount_consumed + amount_past_plan
            )

    def _compare_plan_fund(self, plan_amount, fund_amount):
        """Check total amount plan have to equal rolling amount"""
        fund_amount = self.amount_rolling
        amount_compare = (
            float_compare(
                plan_amount,
                fund_amount,
                precision_rounding=self.currency_id.rounding,
            )
            != 0
        )
        message = _(
            "Planning amount should equal to the released amount {:,.2f} {}".format(
                fund_amount, self.currency_id.symbol
            )
        )
        return amount_compare, message
