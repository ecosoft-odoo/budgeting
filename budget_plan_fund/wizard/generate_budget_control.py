# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class GenerateBudgetControl(models.TransientModel):
    _inherit = "generate.budget.control"

    def _prepare_value_duplicate(self, vals):
        vals_list = super()._prepare_value_duplicate(vals)
        for i, val in enumerate(vals):
            vals_list[i]["fund_ids"] = [(6, 0, val["fund_ids"])]
        return vals_list

    def _prepare_value_plan(self, plan_line):
        vals = [
            {
                "analytic_account_id": x.analytic_account_id,
                "allocated_amount": x.allocated_amount,
                "fund_ids": x.fund_ids.ids,
            }
            for x in plan_line
        ]
        return vals
