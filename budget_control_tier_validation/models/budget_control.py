# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetControl(models.Model):
    _name = "budget.control"
    _inherit = ["budget.control", "tier.validation"]
    _state_from = ["submit"]
    _state_to = ["done"]

    _tier_validation_manual_config = False
