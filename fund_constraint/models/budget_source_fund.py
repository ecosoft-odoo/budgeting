# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetSourceFund(models.Model):
    _inherit = "budget.source.fund"

    fund_constraint_ids = fields.One2many(
        comodel_name="fund.constraint",
        inverse_name="fund_id",
    )
