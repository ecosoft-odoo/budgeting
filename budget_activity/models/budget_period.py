# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetPeriod(models.Model):
    _inherit = "budget.period"

    def _get_control_key_obj(self, control_key, control_id):
        if control_key == "activity_id":
            control = self.env["budget.activity"].browse(control_id)
            control_name = "activity"
            return control, control_name
        return super()._get_control_key_obj(control_key, control_id)

    def _get_filter_template_line(self, all_template_lines, control):
        budget_control_key = self.env.company.budget_control_key
        control_id = control[budget_control_key]
        if budget_control_key == "activity_id":
            return all_template_lines.filtered(
                lambda l: control_id in l.activity_ids.ids
            )
        return super()._get_filter_template_line(all_template_lines, control)
