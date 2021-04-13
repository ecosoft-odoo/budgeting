# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class UpdateConsumedPlan(models.TransientModel):
    _name = "update.consumed.plan"
    _description = "Update Consumed Plan"

    date_to = fields.Date(
        string="End Date",
        default=fields.Date.context_today,
        required=True,
        help="End of date",
    )

    def confirm(self):
        self.ensure_one()
        active_ids = self._context.get("active_ids", [])
        budget_control = self.env["budget.control"].browse(active_ids)
        if budget_control:
            budget_control.update_consumed_plan(self.date_to)
        return True
