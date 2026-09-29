# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    budget_allocation_amount_basis = fields.Selection(
        selection=[
            ("new_budget", "New Budget"),
            ("allocated", "Allocated"),
        ],
        default="new_budget",
        required=True,
        help="Choose whether amounts on Budget Allocation lines represent new "
        "budget or the total allocated amount including forwarded amounts.",
    )
