# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    # Expenses
    def _select_ex_commit(self):
        select_ex_query = super()._select_ex_commit()
        select_ex_query.append("ba.name as activity")
        return select_ex_query

    def _from_ex_commit(self):
        from_ex_commit = super()._from_ex_commit()
        from_ex_commit = "\n".join(
            [
                from_ex_commit,
                "left outer join budget_activity ba \
                    on a.activity_id = ba.id",
            ]
        )
        return from_ex_commit
