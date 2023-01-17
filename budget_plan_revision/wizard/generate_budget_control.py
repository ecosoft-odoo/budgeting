# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class GenerateBudgetControl(models.TransientModel):
    _inherit = "generate.budget.control"

    def _create_budget_controls(self, vals):
        """Update budget control for case new budget in year"""
        revision_number = self._context.get("revision_number", False)
        init_revision = self._context.get("init_revision", True)  # default is true
        vals = [
            {**d, "revision_number": revision_number, "init_revision": init_revision}
            for d in vals
        ]
        return super()._create_budget_controls(vals)
