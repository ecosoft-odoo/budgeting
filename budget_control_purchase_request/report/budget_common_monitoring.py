# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetCommonMonitoring(models.AbstractModel):
    _inherit = "budget.common.monitoring"

    def _get_consumed_sources(self):
        return super()._get_consumed_sources() + [
            {
                "model": ("purchase.request.line", "Purchase Request Line"),
                "type": ("20_pr_commit", "PR Commit"),
                "budget_move": (
                    "purchase_request_budget_move",
                    "purchase_request_line_id",
                ),
                "source_doc": ("purchase_request", "purchase_request_id"),
            }
        ]
