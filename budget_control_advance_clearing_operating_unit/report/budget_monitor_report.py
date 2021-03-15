# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    # Advance
    def _select_av_commit(self):
        select_av_query = super()._select_av_commit()
        select_av_query.append("b.operating_unit_id")
        return select_av_query
