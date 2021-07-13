# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    def _get_operating_unit(self):
        ou_id = super()._get_operating_unit()
        if self._context.get("force_all_ou", False):
            ou_id = self.env["operating.unit"].sudo().search([])
        return ou_id
