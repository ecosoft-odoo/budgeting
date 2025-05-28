# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetCommonMonitoring(models.AbstractModel):
    _inherit = "budget.common.monitoring"

    def _get_consumed_sources(self):
        return super()._get_consumed_sources() + [
            {
                "model": ("request.document", "Request"),
                "type": ("15_rq_commit", "Request Commit"),
                "budget_move": ("request_budget_move", "request_document_id"),
                "source_doc": ("request_order", "request_id"),
            }
        ]
