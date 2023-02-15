# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetPeriod(models.Model):
    _inherit = "budget.period"

    agreement = fields.Boolean(
        string="On Agreement",
        default=True,
        readonly=True,
        help="Control budget on purchase (agreement) approved",
    )

    def _budget_info_query(self):
        query = super()._budget_info_query()
        query["info_cols"]["amount_agreement"] = ("7_agreement_commit", True)
        return query
