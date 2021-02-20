# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetPlanLine(models.Model):
    _inherit = "budget.plan.line"

    fund_ids = fields.Many2many(
        comodel_name="budget.source.fund",
        relation="budget_plan_line_source_fund_rel",
        column1="plan_line_id",
        column2="fund_id",
        string="Funds",
    )
