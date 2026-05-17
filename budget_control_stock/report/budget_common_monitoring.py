# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetCommonMonitoring(models.AbstractModel):
    _inherit = "budget.common.monitoring"

    def _get_consumed_sources(self):
        return super()._get_consumed_sources() + [
            {
                "model": ("stock.move", "Stock Move"),
                "type": ("85_actual_stock", "Actual (Stock)"),
                "budget_move": ("stock_budget_move", "stock_move_id"),
                "source_doc": ("stock_picking", "picking_id"),
            }
        ]
