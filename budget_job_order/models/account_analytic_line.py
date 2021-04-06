# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    job_order_id = fields.Many2one(
        comodel_name="budget.job.order",
        string="Job Order",
        index=True,
        ondelete="restrict",
    )
