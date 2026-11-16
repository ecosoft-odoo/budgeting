# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.tools import SQL


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    @api.model
    def _where_purchase(self) -> SQL:
        return SQL("")

    @api.model
    def _get_sql_branches(self) -> list:
        return super()._get_sql_branches() + [
            self._get_consumed_sql("30_po_commit", self._where_purchase())
        ]
