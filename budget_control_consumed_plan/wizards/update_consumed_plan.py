# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class UpdateConsumedPlan(models.TransientModel):
    _name = "update.consumed.plan"
    _description = "Update Consumed Plan"

    date_to = fields.Date(
        string="End Date",
        default=lambda self: self._default_last_date_period(),
        required=True,
        help="This field is maximum of 'date to' from budget control",
    )

    @api.model
    def _default_last_date_period(self):
        active_ids = self._context.get("active_ids", False)
        budget_control_ids = self.env["budget.control"].browse(active_ids)
        budget_control_ids._get_last_date_period()
        return budget_control_ids._get_last_date_period()

    def confirm(self):
        self.ensure_one()
        active_ids = self._context.get("active_ids", [])
        budget_control = self.env["budget.control"].browse(active_ids)
        if budget_control:
            budget_control.update_consumed_plan(self.date_to)
        return True
