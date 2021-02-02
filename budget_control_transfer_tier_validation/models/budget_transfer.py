# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models


class BudgetTransfer(models.Model):
    _name = "budget.transfer"
    _inherit = ["budget.transfer", "tier.validation"]
    _state_from = ["draft"]
    _state_to = ["transfer"]
