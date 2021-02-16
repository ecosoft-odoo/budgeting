# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    # Purchase
    def _select_po_commit(self):
        select_po_query = super()._select_po_commit()
        select_po_query = ",".join(
            [
                select_po_query,
                "bag.name as activity_group, ba.name as activity",
            ]
        )
        return select_po_query

    def _from_po_commit(self):
        from_po_query = super()._from_po_commit()
        from_po_query = "\n".join(
            [
                from_po_query,
                "left outer join budget_activity ba \
                    on a.activity_id = ba.id",
                "left outer join budget_activity_group bag \
                    on ba.activity_group_id = bag.id",
            ]
        )
        return from_po_query
