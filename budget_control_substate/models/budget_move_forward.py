# Copyright 2021 Ecosoft (<http://ecosoft.co.th>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetMoveForward(models.Model):
    _inherit = ["budget.move.forward", "base.substate.mixin"]
    _name = "budget.move.forward"
    _state_field = "state"
