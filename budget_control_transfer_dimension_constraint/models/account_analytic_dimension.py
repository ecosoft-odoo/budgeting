# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class AccountAnalyticDimension(models.Model):
    _inherit = "account.analytic.dimension"

    budget_transfer_constraint = fields.Boolean(
        default=False,
        help="If checked, this dimemsion's tags will be available "
        "constraint dimension's tags is selected",
    )
