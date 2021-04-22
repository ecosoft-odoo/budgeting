# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    def _get_value_items(self, date_range, kpi_expression):
        items = super()._get_value_items(date_range, kpi_expression)
        activity_group_id = kpi_expression.kpi_id.activity_group_id.id
        for item in items:
            item["activity_group_id"] = activity_group_id
        return items
