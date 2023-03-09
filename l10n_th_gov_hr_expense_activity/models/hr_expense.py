# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def _prepare_expense_from_prline(self, line):
        pr_line = super()._prepare_expense_from_prline(line)
        # Case Advance
        if self.env.context.get("advance"):
            # Change to advance, and activity_id to clearing_activity_id
            av_line = self.env["hr.expense"].new({"advance": True})
            av_line.onchange_advance()
            av_line._compute_from_product_id_company_id()
            av_line = av_line._convert_to_write(av_line._cache)
            # Assign known values
            pr_line["clearing_activity_id"] = pr_line["activity_id"]
            pr_line["activity_id"] = av_line["activity_id"]
        return pr_line
