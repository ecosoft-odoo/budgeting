# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, models
from odoo.tools import float_compare


class BudgetControl(models.Model):
    _inherit = "budget.control"

    @api.depends("item_ids")
    def _compute_amount_rolling(self):
        for rec in self:
            if rec.revision_number > 0:
                super()._compute_amount_rolling()
            else:
                rec.amount_rolling = rec.released_amount

    def _compare_plan_fund(self, plan_amount, fund_amount):
        """ Check total amount plan have to equal rolling amount """
        # TODO: check revision by keep origin
        if self.revision_number < 1 or self._context.get("keep_origin", False):
            fund_amount = self.released_amount
            amount_compare = (
                float_compare(
                    plan_amount,
                    fund_amount,
                    precision_rounding=self.currency_id.rounding,
                )
                != 0
            )
            message = _(
                "you have to plan total amount is equal {:,.2f} {}".format(
                    fund_amount, self.currency_id.symbol
                )
            )
            return amount_compare, message
        return super()._compare_plan_fund(plan_amount, fund_amount)
