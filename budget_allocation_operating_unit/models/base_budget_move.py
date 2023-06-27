# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BaseBudgetMove(models.AbstractModel):
    _inherit = "base.budget.move"

    def _get_budget_source_fund_report(self):
        # Allow query all OU for check budget
        source_fund_report = super()._get_budget_source_fund_report()
        return source_fund_report.with_context(force_all_ou=1)
