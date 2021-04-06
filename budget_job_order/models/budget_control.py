# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    job_order_ids = fields.Many2many(
        comodel_name="budget.job.order",
        string="Plan with job orders",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    def _get_value_items(self, date_range, kpi_expression):
        """ For each item, multiply by the job order """
        items = super()._get_value_items(date_range, kpi_expression)
        if not self.job_order_ids:
            return items
        # With create item by each job order
        new_items = []
        for item in items:
            for job_order in self.job_order_ids:
                new_item = item.copy()
                new_item["job_order_id"] = job_order.id
                new_items.append(new_item)
        return new_items
