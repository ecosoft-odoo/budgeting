# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetSourceFundPlan(models.Model):
    _inherit = "budget.source.fund.plan"

    plan_id = fields.Many2one(
        comodel_name="budget.plan",
    )
