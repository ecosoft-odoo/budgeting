# Copyright 2021 Ecosoft (<http://ecosoft.co.th>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetBalanceForward(models.Model):
    _inherit = ["budget.balance.forward", "base.substate.mixin"]
    _name = "budget.balance.forward"
    _state_field = "state"
