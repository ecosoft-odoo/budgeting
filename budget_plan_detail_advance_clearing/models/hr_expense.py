# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class HRExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def _prepare_clear_advance(self, line):
        """Prepare data clearing"""
        clearing_dict = super()._prepare_clear_advance(line)
        clearing_dict["analytic_tag_ids"] = line.analytic_tag_ids.ids
        return clearing_dict
