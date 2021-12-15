# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountAnalyticDimension(models.Model):
    _inherit = "account.analytic.dimension"

    budget_transfer_constraint = fields.Boolean(
        default=False,
        help="If checked, this dimemsion's tags will be available "
        "constraint dimension's tags is selected",
    )

    @api.model
    def get_model_names(self):
        res = super().get_model_names()
        return res + ["budget.allocation.line", "account.budget.move"]
