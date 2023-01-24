# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    def _get_group_access_all_ou(self):
        """If user have a group access all ou, return True"""
        return super()._get_group_access_all_ou() or self.env.user.has_group(
            "budget_control_operating_unit_access_all.group_all_ou_budget_control"
        )
