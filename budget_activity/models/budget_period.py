# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import UserError


class BudgetPeriod(models.Model):
    _inherit = "budget.period"

    @api.model
    def _get_kpi_by_control_key(self, template_lines, control):
        activity_id = control["activity_id"]
        template_line = self._get_filter_template_line(template_lines, control)
        if len(template_line) == 1:
            return template_line
        # Invalid Template Lines
        activity = self.env["budget.activity"].browse(activity_id)
        if not template_line:
            raise UserError(
                _("Chosen activity %s is not valid in template") % activity.display_name
            )
        raise UserError(
            _(
                "Template Lines has more than one KPI being "
                "referenced by the same account code %s"
            )
            % (activity.display_name)
        )

    def _get_filter_template_line(self, all_template_lines, control):
        """Overwrite filter template line from account_id to activity_id"""
        activity_id = control["activity_id"]
        template_lines = all_template_lines.filtered(
            lambda l: activity_id in l.activity_ids.ids
        )
        return template_lines
