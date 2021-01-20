# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    # Purchase Request
    def _select_pr_commit(self):
        select_pr_query = super()._select_pr_commit()
        select_pr_query = ",".join(
            [
                select_pr_query,
                "bag.name as activity_group, ba.name as activity",
            ]
        )
        return select_pr_query

    def _from_pr_commit(self):
        from_pr_query = super()._from_pr_commit()
        from_pr_query = "\n".join(
            [
                from_pr_query,
                "left outer join budget_activity ba \
                    on a.activity_id = ba.id",
                "left outer join budget_activity_group bag \
                    on ba.activity_group_id = bag.id",
            ]
        )
        return from_pr_query
