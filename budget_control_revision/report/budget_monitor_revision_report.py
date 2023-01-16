# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetMonitorRevisionReport(models.Model):
    _name = "budget.monitor.revision.report"
    _inherit = "budget.monitor.report"
    _description = "Budget Revision Monitoring Report"
    _auto = False
    _order = "date desc"
    _rec_name = "reference"

    def _from_budget(self):
        """To see the previous version, active can be false."""
        sql_from = super()._from_budget()
        return sql_from.replace("and b.active = true", "")
