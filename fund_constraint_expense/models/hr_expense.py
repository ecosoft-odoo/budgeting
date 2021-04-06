# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class HRExpense(models.Model):
    _name = "hr.expense"
    _inherit = ["hr.expense", "fund.docline.mixin"]
    _amount_balance_field = "total_amount"
