# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    def _get_operating_unit(self):
        """Allow user group access all ou can see all budget monitoring"""
        ou_id = super()._get_operating_unit()
        all_ou = self.env.user.has_group(
            "budget_control_operating_unit_access_all.group_all_ou_budget_control"
        )
        if all_ou:
            ou_id = self.env["operating.unit"].sudo().search([])
        return ou_id
