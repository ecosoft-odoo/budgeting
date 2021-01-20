# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    # Advance
    def _select_av_commit(self):
        select_av_query = super()._select_av_commit()
        select_av_query = ",".join(
            [
                select_av_query,
                "bag.name as activity_group, ba.name as activity",
            ]
        )
        return select_av_query

    def _from_av_commit(self):
        from_av_commit = super()._from_av_commit()
        from_av_commit = "\n".join(
            [
                from_av_commit,
                "left outer join budget_activity ba \
                    on a.activity_id = ba.id",
                "left outer join budget_activity_group bag \
                    on ba.activity_group_id = bag.id",
            ]
        )
        return from_av_commit
