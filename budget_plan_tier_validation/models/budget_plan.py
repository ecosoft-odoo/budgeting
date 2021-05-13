# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetPlan(models.Model):
    _name = "budget.plan"
    _inherit = ["budget.plan", "tier.validation"]
    _state_from = ["draft"]
    _state_to = ["confirm", "done"]

    _tier_validation_manual_config = False
