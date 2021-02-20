# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def reset_allocated_amount(cr, registry):
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        BudgetControl = env["budget.control"]
        budget_control = BudgetControl.search([], order="id")
        if budget_control:
            budget_control._compute_allocated_released_amount()
