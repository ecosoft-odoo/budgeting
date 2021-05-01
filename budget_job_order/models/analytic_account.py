# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    job_order_ids = fields.One2many(
        comodel_name="budget.job.order",
        inverse_name="analytic_account_id",
        string="Job Orders",
        help="Create job order from this anlaytic",
    )
