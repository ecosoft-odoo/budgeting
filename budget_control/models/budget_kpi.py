# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetKPI(models.Model):
    _name = "budget.kpi"
    _description = "Budget KPI"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True)
