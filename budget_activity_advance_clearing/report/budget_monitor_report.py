# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    # Advance
    def _select_av_commit(self):
        select_av_query = super()._select_av_commit()
        select_av_query.append("ba.name as activity")
        return select_av_query

    def _from_av_commit(self):
        from_av_commit = super()._from_av_commit()
        from_av_commit = "\n".join(
            [
                from_av_commit,
                "left outer join budget_activity ba \
                    on a.activity_id = ba.id",
            ]
        )
        return from_av_commit
