# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    allocation_line_ids = fields.One2many(
        comodel_name="budget.allocation.line",
        inverse_name="analytic_account_id",
    )
