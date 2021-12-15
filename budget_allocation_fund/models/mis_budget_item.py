# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class MisBudgetItem(models.Model):
    _inherit = "mis.budget.item"

    def search_neutralize(self, dom):
        mis_filter = self._context.get("mis_report_filters", {})
        if mis_filter and len(dom) == 3 and dom[0] == "fund_id":
            return (1, "=", 1)
        return super().search_neutralize(dom)
