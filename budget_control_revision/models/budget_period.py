# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class BudgetPeriod(models.Model):
    _inherit = "budget.period"

    def _budget_info_query(self):
        query = super()._budget_info_query()
        query["fields"].append("revision_number")
        query["groupby"].append("revision_number")
        return query
