# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetCommonMonitoring(models.AbstractModel):
    _inherit = "budget.common.monitoring"

    def _get_consumed_sources(self):
        return super()._get_consumed_sources() + [
            {
                "model": ("hr.expense", "Expense"),
                "type": ("50_ex_commit", "EX Commit"),
                "budget_move": ("expense_budget_move", "expense_id"),
                "source_doc": ("hr_expense_sheet", "sheet_id"),
            }
        ]
