# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetCommonMonitoring(models.AbstractModel):
    _inherit = "budget.common.monitoring"

    def _get_consumed_sources(self):
        return super()._get_consumed_sources() + [
            {
                "model": ("purchase.order.line", "Purchase Line"),
                "type": ("30_po_commit", "PO Commit"),
                "budget_move": ("purchase_budget_move", "purchase_line_id"),
                "source_doc": ("purchase_order", "purchase_id"),
            }
        ]
